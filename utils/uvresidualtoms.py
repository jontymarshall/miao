import numpy as np
import shutil
import os
import pickle

#Read in data parameters; THIS ASSUMES YOU ARE IN THE UVFIT FOLDER
miaopath, casapath, sourcetag, workingdir, vis, nvis = pickle.load(open('../dirvises.npy','rb'))
miaopath=miaopath#.encode('ascii')
sourcetag=sourcetag#.encode('ascii')
vis=[x for x in vis] #[x.encode('ascii') for x in vis]
workingdir=workingdir#.encode('ascii')
#print(vis)

#Read in pixel parameters
dxy, nxy = pickle.load(open('../calibratedms/pixinfo.npy','rb'))

tag=sourcetag
warr=np.load('./evaluation/warr.npy')


msdata=[[] for x in vis]
msresiduals=[[] for x in vis]
msrwdata=[[] for x in vis]
msmodel=[[] for x in vis]

for i in np.arange(nvis):
	print('Processing dataset '+vis[i])
	msdata[i]=workingdir+'/'+sourcetag+'/'+'calibratedms/'+vis[i]
	

	msresiduals[i]=workingdir+'/'+sourcetag+'/calibratedms/'+sourcetag+'_calibratedvis_cont_'+str(i)+'_res.ms'
	#viscur=msresiduals[i]
	os.system('rm -r '+msresiduals[i])
	shutil.copytree(msdata[i], msresiduals[i])

	#Now also make a new vis for reweighted data
	msrwdata[i]=workingdir+'/'+sourcetag+'/calibratedms/'+tag+'_calibratedvis_cont_'+str(i)+'_rwdat.ms'
	os.system('rm -r '+msrwdata[i])
	shutil.copytree(msdata[i], msrwdata[i])

	#And finally one for the model
	msmodel[i]=workingdir+'/'+sourcetag+'/calibratedms/'+tag+'_calibratedvis_cont_'+str(i)+'_model.ms'
	os.system('rm -r '+msmodel[i])
	shutil.copytree(msdata[i], msmodel[i])

	#Get frequency info
	tb.open(msdata[i]+"/SPECTRAL_WINDOW")
	freqs = tb.getcol("CHAN_FREQ")
	rfreq = tb.getcol("REF_FREQUENCY")
	tb.close()

	#Use CASA ms tools to get the channel/spw info
	ms.open(msdata[i])
	spw_info = ms.getspectralwindowinfo()
	nchan = spw_info["0"]["NumChan"]
	npol = spw_info["0"]["NumCorr"]
	ms.close()

	### NOW PUT RESIDUALS IN RESIDUAL MS
	#tb = casac.table() 
	# Use CASA table tools to fill new DATA and WEIGHT
	tb.open(msresiduals[i], nomodify=False)
	# we need to pull the antennas and find where the autocorrelation values are and aren't
	ant1 = tb.getcol("ANTENNA1")
	ant2 = tb.getcol("ANTENNA2")
	flags   = tb.getcol("FLAG")
	#ac = np.where(ant1 == ant2)[0]
	#if ac.size>0:
	#	print "Autocorrelation rows are present in the MS. Cannot deal with such MSs yet, unless those rows are flagged in which case it *should* work (untested)"
	
	#Read residual visibilities
	u, v, Re, Im, w = np.load('./evaluation/'+tag+'_uvtable_datash'+str(i)+'.npy')
	u, v, Re_mod, Im_mod, w = np.load('./evaluation/'+tag+'_uvtable_modelsh'+str(i)+'.npy')
	Re_resid=Re-Re_mod
	Im_resid=Im-Im_mod
	visres=np.zeros(u.size).astype(complex)
	visres.real=Re_resid
	visres.imag=Im_resid
	#HERE get frequency back into visibilities, inverting what was done in mstonumpyortxt.py
	visreswithfreqs = visres.reshape((freqs.shape[0], visres.size//freqs.shape[0]))
	
	#data_array = np.zeros((2, freqs.shape[0], ant1.shape[0])).astype(complex)

	#fill non-flagged data points with residuals
	if npol>=2:
		data_array = np.zeros((2, freqs.shape[0], ant1.shape[0])).astype(complex)
		flags2d = np.logical_or(flags[0,:,:],flags[1,:,:])
		data_array[0,np.logical_not(flags2d)] = visres
		data_array[1,np.logical_not(flags2d)] = visres
		flagstobeput=np.zeros(flags.shape)
		flagstobeput[0,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		flagstobeput[1,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		#data_array[0,:] = visres
		#data_array[1,:] = visres	
		#data_array[0,flags[0,:,:]] = 0 + 0j
		#data_array[1,flags[1,:,:]] = 0 + 0j
		tb.putcol("FLAG", flagstobeput)

	else:
		data_array = np.zeros((1, freqs.shape[0], ant1.shape[0])).astype(complex)
		data_array[0,np.logical_not(flags[0,:,:])] = visres
	
	#Multiplying the weights by best-fit factor found in modelling
	weights = tb.getcol("WEIGHT")
	weights*=warr[i]
		
	tb.putcol("DATA", data_array)
	tb.putcol("WEIGHT", weights)

	# if the MS had a corrected column, remove it (this happens with MS's created with simobserve")
	if ("CORRECTED_DATA" in tb.colnames()):
		tb.removecols("CORRECTED_DATA")

	tb.flush()
	tb.close()

	### NOW PUT MODEL IN MODEL MS
	#tb = casac.table() 
	# Use CASA table tools to fill new DATA and WEIGHT
	tb.open(msmodel[i], nomodify=False)	
	#Multiplying the weights by best-fit factor found in modelling
	weights = tb.getcol("WEIGHT")
	weights*=warr[i]

	visres=np.zeros(u.size).astype(complex)
	visres.real=Re_mod
	visres.imag=Im_mod
	visreswithfreqs = visres.reshape((freqs.shape[0], visres.size//freqs.shape[0]))

	#fill non-flagged data points with residuals
	if npol>=2:
		data_array = np.zeros((2, freqs.shape[0], ant1.shape[0])).astype(complex)
		flags2d = np.logical_or(flags[0,:,:],flags[1,:,:])
		data_array[0,np.logical_not(flags2d)] = visres
		data_array[1,np.logical_not(flags2d)] = visres
		flagstobeput=np.zeros(flags.shape)
		flagstobeput[0,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		flagstobeput[1,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		#data_array[0,:] = visres
		#data_array[1,:] = visres	
		#data_array[0,flags[0,:,:]] = 0 + 0j
		#data_array[1,flags[1,:,:]] = 0 + 0j
		tb.putcol("FLAG", flagstobeput)
	else:
		data_array = np.zeros((1, freqs.shape[0], ant1.shape[0])).astype(complex)
		data_array[0,np.logical_not(flags[0,:,:])] = visres
	
	tb.putcol("DATA", data_array)
	tb.putcol("WEIGHT", weights)
	
	# if the MS had a corrected column, remove it (this happens with MS's created with simobserve")
	if ("CORRECTED_DATA" in tb.colnames()):
		tb.removecols("CORRECTED_DATA")

	tb.flush()
	tb.close()

	#Now fix data MS
	tb.open(msrwdata[i], nomodify=False)
	visres=np.zeros(u.size).astype(complex)
	visres.real=Re
	visres.imag=Im
	visreswithfreqs = visres.reshape((freqs.shape[0], visres.size//freqs.shape[0]))

	#fill non-flagged data points with residuals
	if npol>=2:
		data_array = np.zeros((2, freqs.shape[0], ant1.shape[0])).astype(complex)
		flags2d = np.logical_or(flags[0,:,:],flags[1,:,:])
		data_array[0,np.logical_not(flags2d)] = visres
		data_array[1,np.logical_not(flags2d)] = visres
		flagstobeput=np.zeros(flags.shape)
		flagstobeput[0,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		flagstobeput[1,:,:]=np.logical_or(flags[0,:,:],flags[1,:,:])
		#data_array[0,:] = visres
		#data_array[1,:] = visres	
		#data_array[0,flags[0,:,:]] = 0 + 0j
		#data_array[1,flags[1,:,:]] = 0 + 0j
		tb.putcol("FLAG", flagstobeput)
	else:
		data_array = np.zeros((1, freqs.shape[0], ant1.shape[0])).astype(complex)
		data_array[0,np.logical_not(flags[0,:,:])] = visres


	tb.putcol("DATA", data_array)
	tb.putcol("WEIGHT", weights)
	tb.flush()
	tb.close()
print("Done! _res, _model, and _rwdat CASA MS files have been produced and placed in the ../../calibratedms directory")



