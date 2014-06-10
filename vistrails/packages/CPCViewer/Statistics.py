'''
Created on Mar 24, 2014

@author: tpmaxwel
'''

import numpy
import numpy.ma,cdms2
from grower import grower

class VarType:
    Covariance = 0
    Correlation = 1

class StatisticsError (Exception):
    def __init__ (self, args=None):
        """Create an exception"""
        self.args = args
    def __str__(self):
        """Calculate the string representation"""
        return str(self.args)
    __repr__ = __str__


def __checker(x,y,axes=0):
    # Are the input Variables ?
    xismv=cdms2.isVariable(x)
    yismv=cdms2.isVariable(y)
    if y is None : yismv=1
    ax=None
    if not numpy.ma.isarray(x):
        x=numpy.ma.array(x,copy=0)
    if not numpy.ma.isarray(y) and not y is None:
        y=numpy.ma.array(y,copy=0)
        
    if xismv * yismv !=1:
        if x.shape!=numpy.ma.shape(y) and not y is None:
            raise StatisticsError,'Error x and y shape do not match !'+str(x.shape)+','+str(numpy.ma.shape(y))
        else:
            shy=list(y.shape)
            shy2=y.shape
            shx=list(x.shape)
            myaxes=[axes,]
            for anaxis in myaxes[::-1]:
                shy.insert(0,shx[anaxis])
            y=numpy.ma.resize(y,shy)
            sh=range(len(x.shape))
            if axes!=0:
                for i in range(len(myaxes)):
                    sh[myaxes[i]]=i
                    sh[i]=myaxes[i]
                y=numpy.ma.transpose(y,sh)
            if x.shape!=numpy.ma.shape(y) and not y is None:
                raise StatisticsError,'Error x and y shape do not match (y shouldbe 1D less than x) !'+str(x.shape)+','+str(shy2)+' Remember y must be 1D less than x'
        if type(axes)!=type([]) :
            axes=cdms2.orderparse(str(axes))
        for i in axes:
            if len(x.shape)<i:
                raise StatisticsError,'Error you have '+str(len(x.shape))+' dimensions and try to work on dim:'+str(i)
    else:
        if not y is None:
            x,y=grower(x,y)
            if x.shape!=y.shape :
                raise StatisticsError,'Error x and y have different shapes'+str(x.shape)+', '+str(y.shape)
        ax=x.getAxisList()
        xorder=x.getOrder(ids=1)
        # Now grows w
        if type(axes)==type(1) : axes=str(axes)
        if type(axes)!=type([]):
            axesparse=cdms2.orderparse(axes)
            naxes=len(axesparse)
            for i in range(naxes):
                o=axesparse[i]
                if type(o)==type(''):
                    for j in range(len(xorder)):
                        if xorder[j]==o : axesparse[i]=j
                    if type(axesparse[i])==type(''): # Well it must be a name for x y t....
                        for j in range(len(x.shape)):
                            if o[1:-1]==x.getAxis(j).id:
                                axesparse[i]=j
                    if type(axesparse[i])==type(''): # Everything failed the axis id must be not existing in the slab...
                        raise StatisticsError,'Error axis id :'+o+' not found in first slab: '+x.getOrder(ids=1)
            axes=axesparse
    # Now we have array those shape match, and a nice list of axes let's keep going
    naxes=len(axes)
    n0=1
    xsh=x.shape
    xorder=range(len(x.shape))
    forder=[]
    for i in range(naxes):
        forder.append(axes[i])
        n0=n0*xsh[axes[i]]
    fsh=[n0]
    ax2=[]
    for i in range(len(x.shape)):
        if not i in forder:
            forder.append(i)
            fsh.append(xsh[i])
            if not ax is None: ax2.append(ax[i])
    if not ax is None: ax=ax2
    x=numpy.ma.transpose(x,forder)
    x=numpy.ma.resize(x,fsh)
    if not y is None:
        y=numpy.ma.transpose(y,forder)
        y=numpy.ma.resize(y,fsh)
    if not y is None:
        m=y.mask
        if not m is numpy.ma.nomask:
            x=numpy.ma.masked_where(m,x)
        m=x.mask
        if not m is numpy.ma.nomask:
            y=numpy.ma.masked_where(m,y)

    return x,y,axes,ax

def var( x, y, var_type=VarType.Covariance,  **args ):
    x,y,axes,ax = __checker( x, y )
    
    xmean=numpy.ma.average( x, axis=0)
    ymean=numpy.ma.average( y, axis=0)
    x = x - xmean
    y = y - ymean
    del(xmean)
    del(ymean)
    
    N = x.shape[0] - 1
    cov = numpy.ma.sum( x*y, axis=0 ) / N
        
    if var_type == VarType.Correlation:
        sx=numpy.ma.sqrt( numpy.ma.sum( x*x, axis=0) / N )
        sy=numpy.ma.sqrt( numpy.ma.sum( y*y, axis=0) / N )            
        cov = cov/(sx*sy)
        
    return cov