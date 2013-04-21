import cdms2, sys, os

opendapURL  = "http://nomads.ncep.noaa.gov:9090/dods/fens/fens20130403/fens001_00z"    # This one works!
opendapURL1 = "http://nomads.ncep.noaa.gov:9090/dods/nam/nam20130308/nam1hr_06z"
opendapURL2 = "http://nomads-w4.p.woc.noaa.gov:80/dods/nam/nam20130308/nam_conusnest_18z"
opendapURL3 = "http://nomads.ncep.noaa.gov:80/dods/gfs/gfs20130306/gfs_00z"
opendapURL4 = "http://nomads.ncep.noaa.gov:9090/dods/sref/sref20130330/sref_na_em_n2_15z"
opendapURL5 = "http://goldsmr1.sci.gsfc.nasa.gov:80/dods/MAT3FVCHM"
opendapURL6 = "http://goldsmr2.sci.gsfc.nasa.gov:80/dods/MATMNXSLV"

vname0 = 'tmpprs'
vname1 = 'rhprs'
vname2 = 'vissfc'
vname3 = 'delp'
vname4 = 't500'

vn = vname4
url = opendapURL6

dataset = cdms2.open( url ) 
v = dataset[ vn ]

print "Got variable %s: %s " % ( vn, v.shape )
if (v.rank() == 5):     print "Data Sample: %s" % ( v[ 0, 0, 2:6, 20:25, 20:25 ] )
elif (v.rank() == 4):   print "Data Sample: %s" % ( v[ 10, 2:6, 20:25, 20:25 ] )
else:                   print "Data Sample: %s" % ( v[ 0, 20:25, 20:25 ] )