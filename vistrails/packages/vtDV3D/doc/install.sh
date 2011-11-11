# make html
cd ..
tar cvf vtDV3D.tar doc
gzip vtDV3D.tar
scp ./vtDV3D.tar.gz dp4.nccs.nasa.gov:/portal/web/DV3D/vtDV3D.tar.gz
rm vtDV3D.tar.gz


