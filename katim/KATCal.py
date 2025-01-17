
"""
"""
from . import AIPSLiteTask as AIPSTask
import UV, UVDesc, Image, ImageDesc, FArray, ObitTask, AIPSDir, OErr, History
import InfoList, Table, OSystem, OASDM
from AIPSData import AIPSImage
from AIPS import AIPS
from FITS import FITS
from AIPSDir import AIPSdisks, nAIPS
from OTObit import Acat, AMcat, getname, zap, imhead, tabdest, tput
from Obit import Version
import ObitTalkUtil
# The following imports are not used in this script, but are somehow passed onto another part of the script
# ImageDesc, AIPSImage, AIPS, FITS, AIPSdisks, nAIPS, tput, imhead, tabdest, Acat
from PipeUtil import day2dhms, imstat, setname, setoname
from PipeUtil import getStartStopTime, getSVNVersion, printMess
from PipeUtil import AllDest, FetchObject, SaveObject, XMLAddDescription, XMLSetAttributes
import os, os.path, re, math, copy, pprint, string
import sys
import numpy as np
import itertools
import datetime
import xml.dom.minidom
import katpoint
import katdal
from ObitTalkUtil import FITSDir
from .KATImExceptions import KATUnimageableError

manifest = { 'project' : [],  # list of project output files
             'source'  : {} } # dict of source output files

def KATInitContParms():
    """
    Initialize KAT-7 continuum pipeline parameters

    Reads the name and calss of the AIPS raw uvdata and the metadata extraced from the input h5 file.

    Creates and initializes the parameter dictionary.  Returns python dict with
    parameters.
    """
    ################################################################

    parms = {}
    # General data parameters
    parms["check"]         = False      # Only check script, don't execute tasks
    parms["debug"]         = False      # run tasks debug
    parms["fluxModel"]     = "PERLEY_BUTLER_2013.csv" # Filename of flux calibrator model (in FITS)
    parms["staticflags"]   = "KAT7_SRFI"              # Filename containing a list of frequencies to be flagged (in FITS)

    # User Supplied data parameters
    parms["BPCal"] = []
    parms["ACal"]  = []
    parms["PCal"]  = []
    parms["targets"] = []
    parms["polcal"] = []

    # Archive parameters
    parms["archRoot"]      = "MeerKAT DATA" # Root of ASDM/BDF data
    parms["selBand"]       = "L"   # Selected band, def = first
    parms["selConfig"]     = 1     # Selected frequency config, def = first
    parms["selNIF"]        = 1     # Selected number of IFs, def = first
    parms["Compress"]      = False

    # Hanning
    parms["doHann"]       = True       # Hanning needed for RFI?
    parms["doDescm"]      = True        # Descimate Hanning?

    # Parallactic angle correction
    parms["doPACor"]      = False       # Make parallactic angle correction

    # Special editing list
    parms["doEditList"] =  True         # Edit using editList?
    parms["editFG"]       = 1            # Table to apply edit list to
    parms["doCopyFG"]     = True

    # Editing
    parms["doClearTab"]   = True        # Clear cal/edit tables
    parms["doClearGain"]  = True        # Clear SN and CL tables >1
    parms["doClearFlag"]  = True        # Clear FG tables > 1
    parms["doClearBP"]    = True        # Clear BP tables?
    parms["doQuack"]      = True        # Quack data?
    parms["doBadAnt"]     = False        # Check for bad antennas?
    parms["doInitFlag"]   = True        # Initial broad Frequency and time domain flagging
    parms["doChopBand"]   = True        # Cut the bandpass from lowest to highest channel after special editing.
    parms["editList"]     = []          # List of dictionaries    
    parms["quackBegDrop"] = 7.5/60.0    # Time to drop from start of each scan in min
    parms["quackEndDrop"] = 0./60.0         # Time to drop from end of each scan in min
    parms["quackReason"]  = "Quack"     # Reason string
    parms["begChanFrac"]  = 0.035        # Fraction of beginning channels to drop
    parms["endChanFrac"]  = 0.035        # Fraction of end channels to drop
    parms["doShad"]       = True        # Shadow flagging (config dependent)
    parms["shadBl"]       = 18.0        # Minimum shadowing baseline (m)
    parms["doElev"]       = False       # Do elevation flagging
    parms["minElev"]      = 15.0        # Minimum elevation to keep.
    parms["doFD1"]        = True        # Do initial frequency domain flagging
    parms["FD1widMW"]     = 55          # Width of the initial FD median window
    parms["FD1maxRes"]    = 5.0         # Clipping level in sigma
    parms["FD1TimeAvg"]   = 1.0         # time averaging in min. for initial FD flagging
    parms["FD1baseSel"]   = None        # Baseline fitting region for FD1 (updates by KAT7CorrParms)
    parms["doMednTD1"]    = True        # Median editing in time domain?
    parms["mednSigma"]    = 7.0         # Median sigma clipping level
    parms["mednTimeWind"] = 8.0         # Median window width in min for median flagging
    parms["mednAvgTime"]  = 8.0/60         # Median Averaging time in min
    parms["mednAvgFreq"]  = 1           # Median 1=>avg chAvg chans, 2=>avg all chan, 3=> avg chan and IFs
    parms["mednChAvg"]    = 8           # Median flagger number of channels to average
    parms["doRMSAvg"]    = True         # Edit calibrators by RMSAvg?
    parms["RMSAvg"]      = 3.0          # AutoFlag Max RMS/Avg for time domain RMS filtering
    parms["RMSTimeAvg"]  = 1.0          # AutoFlag time averaging in min.
    parms["doAutoFlag"]  = True         # Autoflag editing after first pass calibration?
    parms["doAutoFlag2"] = True         # Autoflag editing after final (2nd) calibration?
    parms["IClip"]       = None         # AutoFlag Stokes I clipping
    parms["VClip"]       = None         #
    parms["XClip"]       = None         # AutoFlag cross-pol clipping
    parms["timeAvg"]     = 0.5          # AutoFlag time averaging in min. 
    parms["doSecAFFD"]   = True         # do AutoFlag frequency domain flag on second pass
    parms["doFirstAFFD"] = False        # do AutoFlag frequency domain flag on first pass
    parms["FDwidMW"]     = 51           # Width of the median window
    parms["FDmaxRMS"]    = [10.0,0.1]   # Channel RMS limits (Jy)
    parms["FDmaxRes"]    = 7.0          # Max. residual flux in sigma
    parms["FDmaxResBL"]  = 7.0          # Max. baseline residual
    parms["FDbaseSel"]   = None         # Channels for baseline fit (Updated by KAT7CorrParms)
    parms["FDmaxAmp"]    = None         # Maximum average amplitude (Jy)
    parms["FDmaxV"]      = 2.0          # Maximum average VPol amp (Jy)
    parms["minAmp"]      = 1.0e-6       # Minimum allowable amplitude
    parms["BChDrop"]     = None         # number of channels to drop from start of each spectrum
                                        # NB: based on original number of channels, halved for Hanning
    parms["EChDrop"]     = None         # number of channels to drop from end of each spectrum
                                        # NB: based on original number of channels, halved for Hanning
    # Construct a calibrator model from initial image??
    parms["getCalModel"]  =  True

    # Delay calibration
    parms["doDelayCal"]   =  True       # Determine/apply delays from contCals
    parms["delaySolInt"]  =  2.0        # delay solution interval (min)
    parms["delaySmoo"]    =  0.0        # Delay smoothing time (hr)
    parms["doTwo"]        =  True       # Use two baseline combinations in delay cal
    parms["delayZeroPhs"] =  False      # Zero phase in Delay solutions?
    parms["delayBChan"]   =  None       # first channel to use in delay solutions
    parms["delayEChan"]   =  None       # highest channel to use in delay solutions
    parms["delayAvgIF"]   =  False      # Average the IFs during delay calibration
    parms["delayAvgPol"]  =  False      # Average the H and V pols during delay calibration

    # Bandpass Calibration?
    parms["doBPCal"]    =    True       # Determine Bandpass calibration
    parms["bpBChan1"]   =    1        # Low freq. channel,  initial cal
    parms["bpEChan1"]   =    0       # Highest freq channel, initial cal, 0=>all
    parms["bpDoCenter1"] =   0.0       # Fraction of  channels in 1st, overrides bpBChan1, bpEChan1
    parms["bpBChan2"]   =    1          # Low freq. channel for BP cal
    parms["bpEChan2"]   =    0          # Highest freq channel for BP cal,  0=>all
    parms["bpChWid2"]   =    1          # Number of channels in running mean BP soln
    parms["bpdoAuto"]   =    False      # Use autocorrelations rather than cross?
    parms["bpsolMode"]  =    'A&P'      # Band pass type 'A&P', 'P', 'P!A'
    parms["bpsolint1"]  =    15./60     # BPass phase correction solution in min
    parms["bpsolint2"]  =    60.0       # BPass bandpass solution in min 0.0->scan average
    parms["bpUVRange"]  =    [0.0,1.e05]  # uv range for bandpass cal
    parms["specIndex"]  =    0.0        # Spectral index of BP Cal
    parms["doSpecPlot"] =    False       # Plot the amp. and phase across the spectrum

    # Amp/phase calibration parameters
    parms["doAmpPhaseCal"] = True
    parms["refAnt"]   =       0          # Reference antenna
    parms["refAnts"]  =      [0]         # List of Reference antenna for fringe fitting
    parms["solInt"]   =      2.0         # solution interval (min)
    parms["ampScalar"]=     False        # Ampscalar solutions?
    parms["solSmo"]   =      0.0          # Smoothing interval for Amps (min)

    # Apply calibration and average?
    parms["doCalAvg"] =      'Splat'    # calibrate and average cont. calibrator data 
                                        # ('BL'- baseline bept, 'Splat'- Splat)
                                        # If BL, then FOV and maxInt are chosen from imaging
                                        # parameters.
    parms["avgClass"] =      "UVAvg"    # AIPS class of calibrated/averaged uv data
    parms["CalAvgTime"] =    0.         # Time for averaging calibrated uv data (min)
    parms["avgStokes"] =     ' '        # Stokes to extract on average.
    parms["CABIF"] =         1          # First IF to copy
    parms["CAEIF"] =         0          # Highest IF to copy
    parms["chAvg"]   =       None       # No channel average
    parms["avgFreq"] =       None       # No channel average
    parms["doAuto"]  =       False      # Export the AutoCorrs as well.

    # Right-Left delay calibration
    parms["doRLDelay"] =  False             # Determine/apply R-L delays
    parms["RLDCal"]    = [(None,None,None)] # Array of triplets of (name, R-L phase (deg at 1 GHz),
                                            # RM (rad/m**2)) for calibrators
    parms["rlBChan"]   = 1                  # First (1-rel) channel number
    parms["rlEChan"]   = 0                  # Highest channel number. 0=> high in data.
    parms["rlUVRange"] = [0.0,0.0]          # Range of baseline used in kilowavelengths, zeros=all
    parms["rlCalCode"] = '  '               # Calibrator code
    parms["rlDoCal"]   = 2                  # Apply calibration table? positive=>calibrate
    parms["rlgainUse"] = 0                  # CL/SN table to apply, 0=>highest
    parms["rltimerange"]= [0.0,1000.0]      # time range of data (days)
    parms["rlDoBand"]  = 1                  # If > 0 apply bandpass calibration
    parms["rlBPVer"]   = 0                  # BP table to apply, 0=>highest
    parms["rlflagVer"] = 2                  # FG table version to apply
    parms["rlrefAnt"]  = 0                  # Reference antenna, defaults to refAnt

    # Instrumental polarization cal?
    parms["doPolCal"]  =  False      # Determine instrumental polarization from PCInsCals?
    parms["PCInsCals"] = []          # instrumental poln calibrators, name or list of names
    parms["PCFixPoln"] = False       # if True, don't solve for source polarization in ins. cal
    parms["PCpmodel"]  = [0.0,0.0,0.0,0.0,0.0,0.0,0.0]  # Instrumental poln cal source poln model.
    parms["PCAvgIF"]   = False       # if True, average IFs in ins. cal.
    parms["PCSolInt"]  = 2.          # instrumental solution interval (min), 0=> scan average(?)
    parms["PCRefAnt"]  = 0           # Reference antenna, defaults to refAnt
    parms["PCSolType"] = "    "      # solution type, "    ", "LM  "
    parms["doPol"]     = False       # Apply polarization cal in subsequent calibration?
    parms["PDVer"]     = 1           # Apply PD table in subsequent polarization cal?
    parms["PCChInc"]   = 5             # Channel increment in instrumental polarization
    parms["PCChWid"]   = 5             # Channel averaging in instrumental polarization

    # Right-Left phase (EVPA) calibration, uses same  values as Right-Left delay calibration
    parms["doRLCal"]    = False      # Set RL phases from RLCal - RLDCal or RLPCal
    parms["RLPCal"]     = None       # RL Calibrator source name, in None no IF based cal.
    parms["RLPhase"]    = 0.0        # R-L phase of RLPCal (deg) at 1 GHz
    parms["RLRM"]       = 0.0        # R-L calibrator RM (NYI)
    parms["rlChWid"]    = 3          # Number of channels in running mean RL BP soln
    parms["rlsolint1"]  = 10./60     # First solution interval (min), 0=> scan average
    parms["rlsolint2"]  = 5.0       # Second solution interval (min)
    parms["rlCleanRad"] = None       # CLEAN radius about center or None=autoWin
    parms["rlFOV"]      = 0.05       # Field of view radius (deg) needed to image RLPCal

    # Recalibration
    parms["doRecal"]       = True        # Redo calibration after editing
    parms["doDelayCal2"]   = True       # Group Delay calibration of averaged data?, 2nd pass
    parms["doBPCal2"]      = True        # Determine Bandpass calibration, 2nd pass
    parms["doAmpPhaseCal2"]= True        # Amplitude/phase calibration, 2nd pass
    parms["doAutoFlag2"]   = True        # Autoflag editing after final calibration?

    # Imaging  targets
    parms["doImage"]     = True         # Image targets
    parms["targets"]     = []           # List of target sources
    parms["outIClass"]   = "IClean"     # Output target final image class
    parms["Stokes"]      = "I"          # Stokes to image
    parms["Robust"]      = -1.5         # Weighting robust parameter
    parms["FOV"]         = 1.0          # Field of view radius in deg.
    parms["Niter"]       = 50000        # Max number of clean iterations
    parms["minFlux"]     = 0.00008     # Minimum CLEAN flux density
    parms["minSNR"]      = 4.0          # Minimum Allowed SNR
    parms["solPMode"]    = "P"          # Phase solution for phase self cal
    parms["solPType"]    = "    "       # Solution type for phase self cal
    parms["solAMode"]    = "A&P"        # Delay solution for A&P self cal
    parms["solAType"]    = "    "       # Solution type for A&P self cal
    parms["avgPol"]      = False         # Average poln in self cal?
    parms["avgIF"]       = False        # Average IF in self cal?
    parms["maxPSCLoop"]  = 0            # Max. number of phase self cal loops
    parms["minFluxPSC"]  = 0.00008         # Min flux density peak for phase self cal
    parms["solPInt"]     = 0.5          # phase self cal solution interval (min)
    parms["maxASCLoop"]  = 0            # Max. number of Amp+phase self cal loops
    parms["minFluxASC"]  = 0.0001        # Min flux density peak for amp+phase self cal
    parms["solAInt"]     = 1.0           # amp+phase self cal solution interval (min)
    parms["nTaper"]      = 0            # Number of additional imaging multiresolution tapers
    parms["Tapers"]      = [0.0]        # List of tapers in pixels
    parms["do3D"]        = False         # Make ref. pixel tangent to celest. sphere for each facet
    parms["noNeg"]       = False        # F=Allow negative components in self cal model
    parms["BLFact"]      = 1.01         # Baseline dependent time averaging
    parms["BLchAvg"]     = False        # Baseline dependent frequency averaging
    parms["doMB"]        = True         # Use wideband imaging?
    parms["MBnorder"]    = 1            # order on wideband imaging
    parms["MBmaxFBW"]    = 0.05         # max. MB fractional bandwidth (Set by KAT7InitContFQParms)
    parms["PBCor"]       = False         # Pri. beam corr on final image
    parms["antSize"]     = 13.5         # ant. diameter (m) for PBCor
    parms["CleanRad"]    = None         # CLEAN radius (pix?) about center or None=autoWin
    parms["xCells"]      = 0.0            # x-cell size in final image
    parms["yCells"]      = 0.0            # y-cell  "
    parms["nx"]          = []           # x-Size of a facet in pixels
    parms["ny"]          = []           # y-size of a facet in pixels
    parms["Reuse"]       = 0.          # How many CC's to reuse after each self-cal loop??
    parms["minPatch"]    = 0            # Minumum beam patch to subtract in pixels
    parms["OutlierSize"] = 0            # Size of outlier fields
    parms["autoCen"]     = False         # Do autoCen?
    parms["outlierArea"] = 1.5            # Multiple of FOV around phase center to find outlying CC's

    # Final
    parms["doReport"]  =     True       # Generate source report?
    parms["outDisk"]   =     0          # FITS disk number for output (0=cwd)
    parms["doSaveUV"]  =     True       # Save uv data
    parms["doSaveImg"] =     True       # Save images
    parms["doSaveTab"] =     True       # Save Tables
    parms["doCleanup"] =     True       # Destroy AIPS files

    # diagnostics
    parms["plotSource"]    =  None      # Name of source for spectral plot
    parms["plotTime"]      =  [0.,1000.]  # timerange for spectral plot
    parms["doRawSpecPlot"] =  False       # Plot diagnostic raw spectra?
    parms["doSpecPlot"]    =  False       # Plot diagnostic spectra?
    parms["doSNPlot"]      =  True       # Plot SN tables etc
    parms["doDiagPlots"]   =  True       # Plot single source diagnostics
    parms["doKntrPlots"]   =  False      # Contour plots
    parms["doMetadata"]    =  True       # Save source and project metadata
    parms["doHTML"]        =  True       # Output HTML report
    parms["doVOTable"]     =  True       # VOTable

    return parms

# end KAT-7 InitContParms

def KATGetObsParms(obsdata, katdata, parms, logFile):
    """
    Initialise parameters derived from the metadata in the h5 file.

    Inputs:
    obsdata: dictionary containing observational parameters derived in KATH5toAIPS
    parms: parameter dictionary
    Returns:
    parms: updates parameter dictionary
    """

    # Observation parameters
    parms["selChan"]       = obsdata["numchan"]       # Selected number of channels, def = first
    parms["project"]       = obsdata["Aproject"]      # Project name (12 char or less, used as AIPS Name)
    parms["dataClass"]     = obsdata["Aclass"]        # AIPS class of raw uv data
    parms["disk"]          = obsdata["Adisk"]
    parms["KAT7Freq"]      = obsdata["centerfreq"]    # Representive frequency
    parms["KAT7Cfg"]       = obsdata["corrmode"]      # KAT-7 correlator configuraton
    parms["calInt"]        = obsdata["calInt"]        # Calibration table interval (min)
    parms["seq"]           = obsdata["Aseq"]          # Sequence number for AIPS files
    parms["fitsdisk"]      = obsdata["fitsdisk"]

    # Get the longest baseline
    antennas = obsdata["katdata"].ants
    longBline = 0.0
    for ant1,ant2 in itertools.combinations(antennas,2):
        thisBline=np.linalg.norm(ant1.baseline_toward(ant2))
        if thisBline>longBline:
            longBline=thisBline
    parms["longBline"] = longBline

    # Create the editlist array for static flags (on instantiation it contains a flag of the middle channel).
    editList = KAT7EditList(parms["selChan"])
    parms=KATInitContFQParms(katdata, parms)
    # Get bad antennas and update editlist with these
    if parms["doBadAnt"]:
        badants = KATGetBadAnts(obsdata,(0,len(katdata.channel_freqs)))
        for badant in badants:
            mess = "Flagging "+list(obsdata['antLookup'].keys())[list(obsdata['antLookup'].values()).index(badant['Ant'][0])]
            printMess(mess,logFile)
        parms["editList"]=parms["editList"] + badants

    return parms

def KATh5Condition(katdata, caldata, err):
    """This function will modify the katdata object.
    This function is used to condition the katdata object to make it compatible for import 
    into AIPS and imaging.
    This conditioning performed is as follows:
        (1) Convert spaces in target name to underscores.
        (2) Rename bandpass calibrators to sanitised name for flux calibration
        (3) Add calibrator model information for bandpass calibrators.
        (4) If there is no bandpass calibrator in the observation- check for targets with a flux
            model that can then be used as a bandpass calibrator.

    Parameters
    ----------
    katdata: class `katfile.ConcatenatedDataSet` object or class `katfile.H5DataV2` object
        The katfile object on which the conditioning will be performed.
    caldata: class `katfile.catalogue` object.
        The catalogue ojbect of amplitude and bandpass calibtarors
    err: OErr.OErr() 
        Obit error message stack object
    """
    # Loop through targets
    havebpcal=False
    for targ in katdata.catalogue.targets:
        #Replace spaces in the name with underscores
        targ.name=targ.name.replace(' ','_')[0:12]
        #Also remove ':' which AIPS has trouble with
        targ.name=targ.name.replace(':','_')[0:12]
        #Get the nearest calibrator in caldata.
        fluxcal,offset=caldata.closest_to(targ)
        # Update the calibrator flux model
        if offset*3600.0 < 2.0 and 'bpcal' in targ.tags:  
            # 2.0 arcseconds should be close enough...
            targ.flux_model = fluxcal.flux_model
            if targ.name != fluxcal.name:
                targ.name = fluxcal.name
        else:                            # Not a bandpass calibrator
            if 'bpcal' in targ.tags: targ.tags.remove('bpcal')
        if 'bpcal' in targ.tags:
            havebpcal=True
    #Look for flux models only if we don't have a bandpass calibrator
    if not havebpcal:
        callookup = [targ.name for targ in caldata.targets]
        [targ.tags.append('bpcal') for targ in katdata.catalogue.targets if targ.name in callookup]
        bpcals = [targ.name for targ in katdata.catalogue.targets if 'bpcal' in targ.tags]
        if len(bpcals) > 0:
            msg = "No bpcal found in any target tags! Adding bpcal to targets: %s. "%(str(bpcals))
            OErr.PLog(err, OErr.Warn, msg)
            OErr.printErr(err)
            print(msg)

def KATh5Select(katdata, parms, err, **kwargs):
    """This function will modify the katdata object.
    This function is used to select a subset of targets and scans on the katdata object. 
    These selections attenuate the 'view' of the katdata object to only show data that 
    meets the criteria for running the imaging task. Once the selection has been completed, 
    checks are performed and exceptions are raised if the check fails. The operations are 
    performed directly on the katdata object passed in.

    The katdata selections are as follows: 
        (1) Select user requested targets via kwargs. 
        (2) Select targets that have elevation > 20deg.
        (3) Select < 30 calibrators (a limit on obit imager).
        (4) Select the first spectral window (a limit on obit imager)
        (5) Select frequency range (overrideable via kwargs)

    The checks performed on the attenuated view are as follows:
        (1) Check that there are at least 4 antannas.
        (2) Check that there are scans left after the selections. 
        (3) Check that there are targets left after the selections.
        (4) Check that there is at least 1 bandpass calibrator.

    Parameters
    ----------
        katdata: class `katfile.ConcatenatedDataSet` object or class `katfile.H5DataV2` object
            The katfile object on which the selections and checks will be performed.
        err: OErr.OErr()
            Obit error message stack object
        **kwargs:
            Currently can only pass in targets as a kwarg and delay_katdata if doing polcal 

    Raises
    ------
    KATUnimageableError
    """
    #User defined targets
    if kwargs.get('targets'):
        katdata.select(targets=kwargs.get('targets').split(','))

    file_ants = [ant.name for ant in katdata.ants]
    if kwargs.get('dropants'):
        ants_to_remove = kwargs.get('dropants').split(',')
        for ant in ants_to_remove:
            try:
                file_ants.remove(ant)
            except ValueError:
                print("Antenna:", ant, "not in observation. Skipping ...")
                pass
    katdata.select(ants=file_ants, reset='')

    #reducing data selections
    # Tracks only
    katdata.select(scans='track', reset='')

    # Elevation > 20deg.
    good_elevations = []
    for scan, state, target in katdata.scans():
        # Fetch data
        tm = katdata.timestamps[:]
        nint = len(tm)
        el=target.azel(tm[int(nint/2)])[1]*180./math.pi
        if el >= parms['minElev']:
            good_elevations.append(scan)
        else:   # Throw away scans at low elevation
            msg = "Rejecting Scan:%s, Target:%s Elevation %4.1f < %4.1f deg."%(scan,target.name,el,parms['minElev'])
            OErr.PLog(err, OErr.Info, msg)
            OErr.printErr(err)
            print(msg)
    katdata.select(scans=good_elevations, reset='')

    # If we are going to do flagging on import- then don't select cal_rfi
    if kwargs.get('flag'):
        katdata.select(flags='cam,data_lost,ingest_rfi,predicted_rfi', reset='')

    included_targets = []
    included_bpcals = []
    included_gaincals = []
    included_allcals = []
    for target_index in katdata.target_indices:
        target=katdata.catalogue.targets[target_index]
        if 'bpcal' in target.tags:
            included_bpcals.append(target_index)
        elif 'gaincal' in target.tags:
            included_gaincals.append(target_index)
        else:
            included_targets.append(target_index)
    #make list starting with BPcals and then truncate to 30 elements if necessary
    included_allcals = included_bpcals + included_gaincals
    if len(included_allcals) > 30:
        OErr.PLog(err, OErr.Info, "Too many calibrators in file. Truncating to 30.")
        OErr.printErr(err)
        included_allcals = included_allcals[0:30]
    katdata.select(targets=included_allcals+included_targets, reset='')

    # Only select 1 spectral window
    if len(katdata.spectral_windows) > 1:
        OErr.PLog(err, OErr.Info, "The file contains more than one spectral window.\n Will only image the first.")
        OErr.printErr(err)
        #First spectral window is selected by default.

    channel_range=kwargs.get('channel_range')
    nchan=katdata.shape[1]
    if channel_range:
        channel_range = [int(chan_str) for chan_str in channel_range.split(',')]
        first_chan, last_chan = channel_range[0], channel_range[1]
        parms["BChDrop"]=first_chan
        parms["EChDrop"]=katdata.shape[1]-last_chan
    else:
        # Select Channel Range
        BChanFracDrop = int(nchan*parms['begChanFrac'])
        EChanFracDrop = int(nchan*parms['endChanFrac'])

        if parms["BChDrop"]== None:
            parms["BChDrop"]=BChanFracDrop
        if parms["EChDrop"]== None:
            parms["EChDrop"]=EChanFracDrop
        first_chan=parms["BChDrop"]
        last_chan=katdata.shape[1]-parms["EChDrop"]
    chan_after_ifs=(last_chan-first_chan +1)%8
    if chan_after_ifs!=0:
        #Ensure number of channels divides into number of IFs
        first_chan=first_chan+(chan_after_ifs//2)
        last_chan=last_chan-(chan_after_ifs-(chan_after_ifs//2))
        msg = "Trimming %s channnels to divide band into 8 even sized IFs"% (chan_after_ifs,)
        OErr.PLog(err, OErr.Info, msg)
        OErr.printErr(err)
        print(msg)

    parms["BChDrop"]=first_chan
    parms["EChDrop"]=katdata.shape[1]-last_chan

    if (first_chan < 0) or (last_chan >= katdata.shape[1]):
        raise RuntimeError("Requested channel range outside data set boundaries. Set channels in the range [0,%s]" % (katdata.shape[1]-1,))
    chan_range = slice(first_chan, last_chan + 1)

    msg = "\nChannel range %s through %s." % (first_chan, last_chan)
    OErr.PLog(err, OErr.Info, msg)
    OErr.printErr(err)
    print(msg)
    katdata.select(channels=chan_range)

    # More than 4 antennas
    if len(katdata.ants) < 4:
        OErr.PLog(err, OErr.Fatal, "Too few antennas to process image")
        OErr.printErr(err)
        raise KATUnimageableError("Too few antennas to process image")

    # Must have some scans
    if len(katdata.scan_indices) == 0:
        OErr.PLog(err, OErr.Fatal, "No scan of type:track in file to image.")
        OErr.printErr(err)
        raise KATUnimageableError("No scan of type:track in file to image.")

    # Must have some targets (not sure this is needed??)
    if len(katdata.target_indices) == 0:
        OErr.PLog(err, OErr.Fatal, "No targets in file to image.")
        OErr.printErr(err)
        raise KATUnimageableError("No targets in file to image.")

    # Must have a bandpass calibrator
    BPOK=False
    for targ in katdata.target_indices:
        cal=katdata.catalogue.targets[targ]
        #Correct target name for PKS-1934
        if 'bpcal' in cal.tags: BPOK=True
    BPOK = True
    # Check if BPCal exists - exit if not.
    if not BPOK:
        OErr.PLog(err, OErr.Fatal, "No Bandpass calibrator. Can't image this observation.")
        OErr.printErr(err)
        raise KATUnimageableError("No Bandpass calibrator. Can't image this observation.")

    # Only image things with sensible dump rates
    if katdata.dump_period < 0.4:
        OErr.PLog(err, OErr.Fatal, "Dump rate too small for imaging.")
        OErr.printErr(err)
        raise KATUnimageableError("Dump rate too small for imaging.")

    # Do selection on delay_katdata if we need to
    if parms["PolCal"]:
        kwargs['delay_katdata'].select(ants=file_ants, channels=chan_range, 
                                       flags='data_lost,ingest_rfi,predicted_rfi', reset='')

    #Other errors
    if err.isErr:
        OErr.printErrMsg(err, "Error with h5 file")

def KATGetDelayCal(h5file, katdata=None):
    """
    Try and find the delaycal observation associated with this observation
    Raise a ValueError for various reasons if we cant find it.
    Select only the last 'track' scan in the delaycal- which should be the
    noise diode firing.
    Return a properly conditioned katdal object for the delay cal.
    """
    def _get_noise_diode_scan(kd):
        # Get the scan we want from the delaycal observation.
        # A delaycal has two tracks and the second one should have CompScanLabel='corrected'
        kd.select(scans='track,stop', compscans='corrected')
        # Now there should only be the scans we want, find the longest one
        scan_select = -1
        max_scan = 0
        for scan, _, _ in kd.scans():
            scan_length = len(kd.dumps)
            if scan_length > max_scan:
                max_scan, scan_select = scan_length, scan
        if scan_select >= 0:
            kd.select(scans=scan_select)
            return kd
        return None

    if katdata is None:
        dc_katdata = katdal.open(h5file)
        dc_datdata = _get_noise_diode_scan(dc_katdata)
        if dc_katdata is not None:
            return dc_katdata
    else:
        try:
            sb_cbids = katdata.source.telstate.get_range('sdp_capture_block_id', st=0)
        except KeyError:
            raise ValueError('Cannot find capture blocks associated with this observation.')
        # Lookup CBIDs in current subarray in reverse order and extract delaycal obs.
        delay_cbids = [cbid[0] for cbid in sb_cbids[::-1]
                       if 'calibrate_delays.py' in 
                       katdata.source.telstate.view(cbid[0])['obs_params']['script_name']]
        if len(delay_cbids) == 0:
            raise ValueError('No delay calibration in this schedule block. Cannot do polcal.')
        # Get the scan we want from the delaycal observation.
        # And lets do some rudimentary checks that this delay cal is good for what we want.
        OK = False
        for cbid in delay_cbids:
            dc_katdata = katdal.open(h5file, capture_block_id=cbid)
            dc_datdata = _get_noise_diode_scan(dc_katdata)
            if dc_katdata is not None:
                return dc_katdata
    raise ValueError('Could not find a valid delay calibration for this schedule block.'
                     ' Cannot do polcal.')

def KATInitTargParms(katdata,parms,err):
    """
    Update the target paramaters for the pipeline using the metadata
    extracted from the h5 file.
    Also check the uv data and remove targets which have been removed from the data.
    """
    # Sources
    # Check if user has supplied them
    if len(parms["BPCal"])>0:
        bpcal = [katdata.catalogue[cal] for cal in parms["BPCal"] if cal is not None]
    elif parms['PolCal']:
        alltargs = [katdata.catalogue.targets[cal].name for cal in katdata.target_indices]
        bpcal = [katdata.catalogue.targets[cal] for cal in katdata.target_indices if katdata.catalogue.targets[cal].name == parms['XYtarg']]
        parms['BPCal'] = [targ.name for targ in bpcal]
    else:
    #Otherwise get them from the katfile object
        bpcal = [katdata.catalogue.targets[cal] for cal in katdata.target_indices if 'bpcal' in katdata.catalogue.targets[cal].tags]
        parms["BPCal"] = [katdata.catalogue.targets[cal].name for cal in katdata.target_indices if 'bpcal' in katdata.catalogue.targets[cal].tags]

    if len(parms["ACal"])>0:
        ampcal = [katdata.catalogue[cal] for cal in parms["ACal"] if cal is not None]
    else:
        ampcal = [katdata.catalogue.targets[cal] for cal in katdata.target_indices if 'bpcal' in katdata.catalogue.targets[cal].tags]
        parms["ACal"] = [katdata.catalogue.targets[cal].name for cal in katdata.target_indices if 'bpcal' in katdata.catalogue.targets[cal].tags]

    if len(parms["PCal"])>0:
        gaincal = [katdata.catalogue[cal] for cal in parms["PCal"] if cal is not None]
    else:
        gaincal = [katdata.catalogue.targets[cal] for cal in katdata.target_indices if 'gaincal' in katdata.catalogue.targets[cal].tags]
        parms["PCal"] = [katdata.catalogue.targets[cal].name for cal in katdata.target_indices if 'gaincal' in katdata.catalogue.targets[cal].tags]

    polcal  = []                # Place-holder for polarisation calibrator

    if len(parms["targets"])>0:
        source = []             # Desired targets are already in the parameter list.
    else:
        for cal in katdata.target_indices: parms["targets"].append(katdata.catalogue.targets[cal].name[0:12])   #All Sources
    parms["targets"] = list(set(parms["targets"])) # Remove duplicates
    parms["BPCal"] = list(set(parms["BPCal"]))
    parms["ACal"] = list(set(parms["ACal"]))
    parms["PCal"] = list(set(parms["PCal"]))
    # Do this here to catch user input targets with spaces in the name.
    parms["targets"] = [targ.replace(' ','_') for targ in parms["targets"]]

    # Get the band of observation
    sw = katdata.spectral_windows[katdata.spw]
    band = sw.band

    # Now make calibrater model dicts.
    # Bandpass calibrators
    parms["BPCals"]=parms.get("BPCals",[])
    if not parms["BPCals"]:
        for cal in parms["BPCal"]:
            #Try and find a bpcal model in disk 1
            modelfile = f'{cal[0:12]}{band}Model.fits'
            if os.path.isfile(FITSDir.FITSdisks[1] + modelfile):
                model=EVLACalModel(cal[0:12],CalDisk=1,CalDataType='FITS',CalFile=modelfile,CalCCVer=1,CalCmode='COMP',CalNfield=1)
            else:
                model=EVLACalModel(cal[0:12])
            parms["BPCals"].append(model)

    # Check the best bandpass calibrator to plot
    # Check for source in SU table and only use bpcal with the most visibilities
    if not parms["plotSource"]:
        maxvis=0
        for thistarget in parms["BPCal"]:
            numvis=0
            for scan, state, target in katdata.scans():
                if target.name == thistarget:
                   numvis += katdata.shape[0]
            if numvis > maxvis:
                parms["plotSource"] = thistarget
                maxvis = numvis

    # Amplitude Calibrators
    parms["ACals"]= parms.get("ACals",[])
    if not parms["ACals"]:
        for cal in parms["ACal"]:
            #Try and find a model in disk 1
            modelfile = f'{cal[0:12]}{band}Model.fits'
            if os.path.isfile(FITSDir.FITSdisks[1] + modelfile):
                model=EVLACalModel(cal[0:12],CalDisk=1,CalDataType='FITS',CalFile=modelfile,CalCCVer=1,CalCmode='COMP',CalNfield=1)
            else:
                model=EVLACalModel(cal[0:12])
            parms["ACals"].append(model)

    # Gain Calibrators
    # Amp/phase calibration
    parms["PCals"]=parms.get("PCals",[])
    if not parms["PCals"]:
        PCals = []
        tcals = []
        for cal in parms["PCal"]:
            PCals.append(EVLACalModel(cal[0:12]))
            tcals.append(cal)
        # Check for standard model
        EVLAStdModel(PCals, parms["KAT7Freq"])
        parms["PCals"]          = PCals   # Phase calibrator(s)

    # Delay Calibrators
    parms["DCals"]= parms.get("DCals",[])
    # Ony delay on XYtarg if we do PolCal
    if parms['PolCal']:
        parms["DCals"] = parms["BPCals"]
    else:
        if not parms["DCals"]:
            DCals = []
            tcals = []
            for cal in parms["ACals"] + parms["BPCals"] + parms["PCals"]:
                if not cal['Source'] in tcals:
                    DCals.append(cal)
                    tcals.append(cal['Source'])
            # Check for standard model
            #EVLAStdModel(DCals, parms["KAT7Freq"])
            parms["DCals"]          = DCals      # delay calibrators



#Done KATInitCalModel

def KATGetStaticFlags(katdata,staticflagfile):

    """
    Construct a list of static flags.

    staticflagfile   = path to file containing list of frequency ranges to reject
    katdata          = the KAT7 metadata

    returns: a properly formattted list of edit dictionaries for use with the kat-7 pipeline
    """
    # Get the channel_freqs array from the obsdata database
    channel_freqs=katdata.channel_freqs
    channel_width=katdata.channel_width
    channels=katdata.channels
    padding=20                                   #Pad the start and the end of a flag range in MHz
    #Get the list of frequency ranges from staticflagfile and find flags
    editlist=[]
    with open(staticflagfile) as f:
        for line in f:
            line = line.partition('#')[0]      # Ignore comments
            line = line.split()
            if len(line) == 3:                 # Only use lines with data
                name=line[0]
                startFreq=(float(line[1])-padding)*1e6
                endFreq=(float(line[2])+padding)*1e6
                thisflag = channels[(channel_freqs>startFreq) & (channel_freqs<endFreq)]
                if len(thisflag)>0:                   # We have some bandwidth to flag!!
                    flag_start = thisflag[0] + 1      # +1 for AIPS channel convention
                    flag_end   = thisflag[-1] + 1     # +1 for AIPS channel convention
                    editdict={"timer":("0/00:00:0.0","5/00:00:0.0"),"Ant":[0,0],"IFs":[1,1],"Chans":[int(flag_start),int(flag_end)], "Stokes":'1111',"Reason":name}
                    editlist.append(editdict)
    return(editlist)


def KATGetBadAnts(obsdata,specrange):
    """
    Check the data for bad antennas by calculating Stokes I over specrange channels
    from the Auto-Correlations on the highest elevation scan from selected targets 
    and looking for outliers using the median absolute deviation.

    Inputs: 
    obsdata: metadata dict from KATH5toAIPS 
    specrange: tuple selecting minimum and maximum channels to use

    Outputs:
    editlist: A list of editlist dicts with each entry containing an antenna to be flagged
    """
    
    katdata=obsdata["katdata"]
    targs = obsdata["bpcal"]
    # Get data from the highest elevation scan from checktargs in katdata
    el=0
    #Exit gracefully if we don't have anything to check
    if len(targs)==0:
        return []
    for scan, state, target in katdata.scans():
        if state == 'track' and target in targs:
            tm=katdata.timestamps[:]
            nint=len(tm)
            thisel = target.azel(tm[int(nint/2)])[1]*180./math.pi
            if thisel > el:
                # Highest elevation so far
                el  = thisel
                vis = katdata.vis[:]
                wt  = katdata.weights()[:]
                # Apply flags
                wt  = np.where(katdata.flags()[:],0.0,wt)

    pol_data = np.zeros((len(obsdata['ants']),2))
    # Get stokes I for the chosen scan on each antenna
    for corrnum,corrprod in enumerate(obsdata['products']):
        #AutoCorr and not cross pol
        if corrprod[0]==corrprod[1] and corrprod[2]<2:
            avvis = np.average(np.abs(vis[:,specrange[0]:specrange[1],corrnum]),weights=wt[:,specrange[0]:specrange[1],corrnum])
            pol_data[corrprod[0]-1,corrprod[2]]=avvis

    stokesI = pol_data[:,0] + pol_data[:,1]
    
    # Get the median absolute deviation
    medI = np.median(stokesI)
    MAD = np.median(np.abs(stokesI - medI))
    
    # Reject antennas >10MAD'S from the median
    rejectList=[]
    cutoff=medI - (10.0*MAD)
    for antnum,thisI in enumerate(stokesI):
        if thisI<cutoff:
            rejectList.append({"timer":("0/00:00:0.0","5/00:00:0.0"),"Ant":[antnum+1 ,0],"IFs":[1,1],"Chans":[0,0], "Stokes":'1111',"Reason":"Bad Ant"})
            
    return rejectList


def KAT7EditList(numchannels):

    # Flag the middle channel
    outchannels=int(numchannels/2)
    # Flag the middle channels.
    editlist = [
        {"timer":("0/00:00:0.0","5/00:00:0.0"),"Ant":[ 0,0],"IFs":[1,1],"Chans":[int(outchannels)-1,int(outchannels)+1], "Stokes":'1111',"Reason":"Bad Ch"}
        ]
    return editlist


def KATInitContFQParms(katdata,parms):
    """
    Initialize KAT continuum pipeline frequency dependent parameters

    Some values only set if None on input
    katdata    = katfile object
    parms      = Project parameters, modified on output
    """
    ################################################################
    refFreq   = parms["KAT7Freq"]
    nchan     = parms["selChan"]

    bandwidth = katdata.channel_freqs[-1] - katdata.channel_freqs[0]

    antSize   = 13.5
    blSize    = parms["longBline"]
    doHann    = parms["doHann"]

    # Delay channels
    if parms["delayBChan"] == None:
        parms["delayBChan"] =  1              # first channel to use in delay solutions
    if parms["delayEChan"] == None:
        parms["delayEChan"] =  0  # highest channel to use in delay solutions

    # BPCal channels
    if parms["bpBChan2"] == None:
        parms["bpBChan2"] = 1
    if parms["bpEChan2"] == None:
        parms["bpEChan2"] = 0

    # Amp cal channels
    if parms["doAmpPhaseCal"]==None:
        parms["doAmpPhaseCal"] = True                            # Amplitude/phase calibration
    parms["ampBChan"]  =  1                                      # first channel to use in A&P solutions
    parms["ampEChan"]  =  0                                      # highest channel to use in A&P solutions
    parms["doAmpEdit"] =  True                                   # Edit/flag on the basis of amplitude solutions
    parms["ampSigma"]  =  20.0                                   # Multiple of median RMS about median gain to clip/flag
    # Should be fairly large
    parms["ampEditFG"] =  2                                      # FG table to add flags to, <=0 -> no FG entries

    # Ipol clipping levels
    if parms["IClip"]==None:
        if refFreq<1.0e9:
            parms["IClip"] = [20000.,0.1]  # Allow Cygnus A
        else:
            parms["IClip"] = [200.,0.1]    # Covers most real sources
        # end IPol clipping
    if (parms["FDmaxAmp"]==None):
        parms["FDmaxAmp"]    = parms["IClip"][0]     # Maximum average amplitude (Jy)


    if parms["FDbaseSel"]==None:
        parms["FDbaseSel"] = [1, 0, 1, 0]
    # Set spectral baseline for FD1 flagging ignoring end channels
    if parms["FD1baseSel"]==None:
        parms["FD1baseSel"] = parms["FDbaseSel"]

    # Channel averaging before imaging
    # Can probably set this automatically to accomodate bandwidth smearing constraints later on..
    if parms["chAvg"] == None:
        parms["chAvg"] = 2
    if parms["avgFreq"] == None:
        parms["avgFreq"] = 1

    if parms["doMB"] == None:
        if bandwidth>50e6:                               # Wideband
            parms["doMB"] = True
            if parms["MBmaxFBW"]==None: parms["MBmaxFBW"] = 0.05
            if parms["MBnorder"]==None: parms["MBnorder"] = 1
        else:                                             # Narrow-band
            parms["doMB"] = False

    return parms
# end KATInitContFqParms


def EVLAClearCal(uv, err, doGain=True, doBP=False, doFlag=False,
                 check=False, logfile=""):
    """
    Clear previous calibration

    Delete all SN tables, all CL but CL 1

    * uv       = UV data object to clear
    * err      = Obit error/message stack
    * doGain   = If True, delete SN and CL tables
    * doBP     = If True, delete BP tables
    * doFlag   = If True, delete FG tables except FG=1
    * check    = Only check script, don't execute tasks
    """
    ################################################################
    # Only checking?
    if check:
        return
    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    # Gain tables
    if doGain:
        mess =  "Delete Delete all SN tables"
        printMess(mess, logfile)
        uv.ZapTable("AIPS SN",-1,err)
        ver = uv.GetHighVer("AIPS CL")
        while (ver>1):
            mess =  "Delete CL table %d" % (ver)
            printMess(mess, logfile)
            uv.ZapTable ('AIPS CL', ver, err)
            ver = ver-1
    # Bandpass
    if doBP:
        mess =  "Delete Delete all BP tables"
        printMess(mess, logfile)
        uv.ZapTable("AIPS BP",-1,err)
    # Flag tables
    if doFlag:
        ver = uv.GetHighVer("AIPS FG")
        while (ver>1):
            mess =  "Delete FG table %d" % (ver)
            printMess(mess, logfile)
            uv.ZapTable ('AIPS FG', ver, err)
            ver = ver-1
    OErr.printErrMsg(err, "EVLAClearCal: Error reseting calibration")
    # end EVLAClearCal

def KATCopyFG(uv, err, inVer=1, outVer=2, logfile='', check=False, debug = False):
    """
    Copy AIPS FG table from inVer to outVer

    Returns task error code, 0=OK, else failed

    * uv       = UV data object to copy
    * err      = Obit error/message stack
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    taco = ObitTask.ObitTask("TabCopy")
    try:
        taco.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv, taco)
    taco.outName  = taco.inName
    taco.outClass = taco.inClass
    taco.outDisk  = taco.inDisk
    taco.outSeq   = taco.inSeq
    taco.inTab    = "AIPS FG"
    taco.inVer    = inVer
    taco.outVer   = outVer
    taco.taskLog = logfile
    if debug:
        taco.debug = debug
        taco.i
    # Trap failure
    try:
        if not check:
            taco.g
    except Exception as exception:
        print(exception)
        mess = "Copy of FG table Failed retCode="+str(taco.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLACopyFG

def EVLACopyTable(inObj, outObj, inTab, err, inVer=1, outVer=0,
                  logfile='', check=False, debug = False):
    """
    Copy AIPS Table

    Returns task error code, 0=OK, else failed

    * inObj    = Input Object (UV or Image)
    * outObj   = Output object
    * inTab    = Table type, e.g. "AIPS AN"
    * err      = Obit error/message stack
    * inVer    = intput version
    * outVer   = output version
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    mess =  "Copy "+inTab+" Table "+str(inVer)+" to "+str(outVer)
    printMess(mess, logfile)
    taco = ObitTask.ObitTask("TabCopy")
    try:
        taco.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(inObj, taco)
        setoname(outObj, taco)
    taco.inTab    = inTab
    taco.inVer    = inVer
    taco.outVer   = outVer
    taco.taskLog  = logfile
    if debug:
        taco.debug = debug
        taco.i
    # Trap failure
    try:
        if not check:
            taco.g
    except Exception as exception:
        print(exception)
        mess = "Copy of "+inTab+" table Failed retCode="+str(taco.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLACopyTable


def KATHann(inUV, Aname, Aclass, Adisk, Aseq, err, doDescm=True, \
             flagVer=-1, logfile='', zapin=True, check=False, debug=False):
    """ Hanning smooth a file to AIPS

    Returns task error code, 0=OK, else failed
    inUV       = UV data to smooth
    Aname      = AIPS name of file
    Aclass     = AIPS class of file
    Aseq       = AIPS sequence number of file, 0=> create new
    Adisk      = FITS directory number
    doDescm    = If True descimate (drop alternate) channels
    err        = Python Obit Error/message stack
    check      = Only check script, don't execute tasks
    debug      = Run tasks debug, show input
    logfile    = logfile for messages
    returns AIPS UV data object, None on failure
    """
    ################################################################
    mess =  "Hanning smooth data"
    printMess(mess, logfile)
    #
    hann=ObitTask.ObitTask("Hann")
    try:
        hann.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    setname(inUV,hann)
    if check:
        return inUV
    hann.outName  = Aname[0:12]
    hann.outClass = Aclass[0:6]
    hann.outSeq   = Aseq
    hann.outDisk  = Adisk
    hann.flagVer  = flagVer
    hann.doDescm  = doDescm
    hann.taskLog  = logfile
    hann.debug    = debug
    if debug:
        hann.i
    # Trap failure
    try:
        if not check:
            hann.g
    except Exception as exception:
        print(exception)
        mess = "Median flagging Failed retCode="+str(hann.retCode)
        printMess(mess, logfile)
        return None
    else:
        pass
    # Get output
    outUV = UV.newPAUV("AIPS UV DATA", Aname, Aclass, Adisk, Aseq, True, err)
    if err.isErr:
        mess =  "Error Getting Hanning smoothed data"
        printMess(mess, logfile)
        return None
    if zapin:
        #Zap input
        inUV.Zap(err)
    return outUV
    # end EVLAHann


def EVLAImFITS(inImage, filename, outDisk, err, fract=None, quant=None, \
          exclude=["AIPS HI","AIPS PL","AIPS SL"], include=["AIPS CC"],
          headHi=False, logfile=""):
    """
    Write AIPS image as FITS
    
    Write a Image data set as a FITAB format file
    History also copied

    * inImage    = Image data to copy
    * filename   = name of FITS file, any whitespace characters replaced with underscore
    * outDisk    = FITS directory number
    * err        = Python Obit Error/message stack
    * fract      = Fraction of RMS to quantize
    * quant      = quantization level in image units, has precedence over fract
      None or <= 0 => use fract.
    * exclude    = List of table types NOT to copy
      NB: "AIPS HI" isn't really a table and gets copied anyway
    * include    = List of table types to copy
    * headHi     = if True move history to header, else leave in History table
    """
    ################################################################
    mess =  "Write Image to FITS "+filename+" on disk "+str(outDisk)
    printMess(mess, logfile)
    #
    # Checks
    if not Image.PIsA(inImage):
        raise TypeError("inImage MUST be a Python Obit Image")
    if not OErr.OErrIsA(err):
        raise TypeError("err MUST be an OErr")
    #
    # Deblank filename
    fn = re.sub('\s','_',filename)
    # Set output
    outImage = Image.newPFImage("FITS Image DATA", fn, outDisk, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating FITS data")
    # Check for valid pixels
    if inImage.Desc.Dict["maxval"]<=inImage.Desc.Dict["minval"]:
        fract=None; quant=None
    # Copy
    if fract or quant:
        Image.PCopyQuantizeFITS (inImage, outImage, err, fract=fract, quant=quant)
    else:
        Image.PCopy (inImage, outImage, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error copying Image data to FITS")
    # Copy History
    inHistory  = History.History("inhistory",  inImage.List, err)
    outHistory = History.History("outhistory", outImage.List, err)
    History.PCopy(inHistory, outHistory, err)
    # Add this programs history
    outHistory.Open(History.READWRITE, err)
    outHistory.TimeStamp(" Start Obit imtab",err)
    if fract:
        outHistory.WriteRec(-1,"imtab   / Quantized at "+str(fract)+" RMS",err)
    outHistory.WriteRec(-1,"imtab   / FITS file "+fn+", disk "+str(outDisk),err)
    outHistory.Close(err)
    # History in header?
    if headHi:
        # Copy back to header
        inHistory  = History.History("inhistory",  outImage.List, err)
        History.PCopy2Header (inHistory, outHistory, err)
        # zap table
        outHistory.Zap(err)
    OErr.printErrMsg(err, "Error with history")
    # Copy Tables
    Image.PCopyTables (inImage, outImage, exclude, include, err)
    del outImage
    # end EVLAImFITS


def KATImFITS(inImage, filename, outDisk, err, fract=None, quant=None, \
          exclude=["AIPS HI","AIPS PL","AIPS SL"], include=["AIPS CC"],
          headHi=False, logfile=""):
    """
    Write AIPS image as FITS

    Write a Image data set as a FITAB format file
    History also copied

    * inImage    = Image data to copy
    * filename   = name of FITS file, any whitespace characters replaced with underscore
    * outDisk    = FITS directory number
    * err        = Python Obit Error/message stack
    * fract      = Fraction of RMS to quantize
    * quant      = quantization level in image units, has precedence over fract
      None or <= 0 => use fract.
    * exclude    = List of table types NOT to copy
      NB: "AIPS HI" isn't really a table and gets copied anyway
    * include    = List of table types to copy
    * headHi     = if True move history to header, else leave in History table
    """

    mess =  "Write Image to FITS "+filename+" on disk "+str(outDisk)
    printMess(mess, logfile)
    #
    # Checks
    if not Image.PIsA(inImage):
        raise TypeError("inImage MUST be a Python Obit Image")
    if not OErr.OErrIsA(err):
        raise TypeError("err MUST be an OErr")
    #
    # Deblank filename
    fn = re.sub('\s','_',filename)
    #
    # First convert to AIPS (This might not be needed- but just to make sure)
    # Set output
    outImage = Image.newPAImage("FITS Image DATA", "TEMP", "TEMP", 1, 1, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating FITS data")
    # Copy
    Image.PCopy (inImage, outImage, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error copying FITS data to AIPS")
    # Copy Tables
    Image.PCopyTables (inImage, outImage, exclude, include, err)

    # Add output directory to the environment so AIPS can see it
    if os.path.exists(fn):
        os.remove(fn)
    pth,fnn=os.path.split(fn)
    if not pth:
        os.environ['FTD']=os.environ['PWD']
    else:
        os.environ['FTD']=pth
    
    #Now use FITTP to write out uv data properly so CASA can read it in.
    fittp=AIPSTask.AIPSTask("fittp")
    try:
        fittp.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass    
    setname(outImage, fittp)
    
    fittp.dataout='FTD:'+fnn
    fittp.g
    os.unsetenv('FTD')
    outImage.Zap(err)
    del outImage


def KATUVFITS(inUV, filename, outDisk, err, compress=False, \
              exclude=["AIPS HI", "AIPS SL", "AIPS PL"], \
                  include=["AIPS AN", "AIPS FQ", "AIPS SU"], headHi=False, logfile=""):
    """
    Write UV data as FITS file
    
    Write a UV data set as a FITAB format file
    History written to header

    * inUV       = UV data to copy
    * filename   = name of FITS file, any whitespace characters replaced with underscore 
    * outDisk    = FITS directory number
    * err        = Python Obit Error/message stack
    * exclude    = List of table types NOT to copy
      NB: "AIPS HI" isn't really a table and gets copied anyway
    * include    = List of table types to copy (FQ, AN always done )
      Exclude has presidence over include
    * headHi     = if True move history to header, else leave in History table

    returns FITS UV data object
    """
    ################################################################
    mess =  "Write Data to FITS UV data "+filename+" on disk "+str(outDisk)
    printMess(mess, logfile)

    # Checks
    if not UV.PIsA(inUV):
        raise TypeError("inUV MUST be a Python Obit UV")
    if not OErr.OErrIsA(err):
        raise TypeError("err MUST be an OErr")
    #
    # First convert to AIPS (This might not be needed- but just to make sure)
    # Deblank filename
    fn = re.sub('\s','_',filename)
    # Set output
    outUV = UV.newPAUV("AIPS UV DATA", 'TEMP', 'TEMP', 1, 1, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating AIPS data")
    # Copy
    UV.PCopy (inUV, outUV, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error copying UV data to AIPS")
    # Copy Tables
    UV.PCopyTables (inUV, outUV, exclude, include, err)

    # Add output directory to the environment so AIPS can see it
    if os.path.exists(fn):
        os.remove(fn)
    pth,fnn=os.path.split(fn)
    if not pth:
        os.environ['FTD']=os.environ['PWD']
    else:
        os.environ['FTD']=pth
    
    #Now use FITTP to write out uv data properly so CASA can read it in.
    fittp=AIPSTask.AIPSTask("fittp")
    try:
        fittp.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass    
    setname(outUV, fittp)
    
    fittp.dataout='FTD:'+fnn
    fittp.g
    os.unsetenv('FTD')
    #zap the image
    outUV.Zap(err)
    del outUV
    #return outUV

    # end KATUVFITS

def KATUVFITab(inUV, filename, outDisk, err, compress=False, \
              exclude=["AIPS HI", "AIPS SL", "AIPS PL"], \
                  include=["AIPS AN", "AIPS FQ", "AIPS SU"], headHi=False, logfile=""):
    """
    Write UV data as AIPS FITTAB format
    
    Write a UV data set as a FITAB format file
    History written to header

    * inUV       = UV data to copy
    * filename   = name of FITS file, any whitespace characters replaced with underscore 
    * outDisk    = FITS directory number
    * err        = Python Obit Error/message stack
    * exclude    = List of table types NOT to copy
      NB: "AIPS HI" isn't really a table and gets copied anyway
    * include    = List of table types to copy (FQ, AN always done )
      Exclude has presidence over include
    * headHi     = if True move history to header, else leave in History table

    returns FITS UV data object
    """
    ################################################################
    mess =  "Write Data to FITS UV data "+filename+" on disk "+str(outDisk)
    printMess(mess, logfile)

    # Checks
    if not UV.PIsA(inUV):
        raise TypeError("inUV MUST be a Python Obit UV")
    if not OErr.OErrIsA(err):
        raise TypeError("err MUST be an OErr")
    #
    # First convert to AIPS (This might not be needed- but just to make sure)
    # Deblank filename
    fn = re.sub('\s','_',filename)
    # Set output
    outUV = UV.newPAUV("AIPS UV DATA", 'TEMP', 'TEMP', 1, 1, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating AIPS data")
    # Copy
    UV.PCopy (inUV, outUV, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error copying UV data to AIPS")
    # Copy Tables
    UV.PCopyTables (inUV, outUV, exclude, include, err)

    # Add output directory to the environment so AIPS can see it
    if os.path.exists(fn):
        os.remove(fn)
    pth,fnn=os.path.split(fn)
    if not pth:
        os.environ['FTD']=os.environ['PWD']
    else:
        os.environ['FTD']=pth
    
    #Now use FITTP to write out uv data properly so CASA can read it in.
    fittp=AIPSTask.AIPSTask("fitab")
    try:
        fittp.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass    
    setname(outUV, fittp)
    
    fittp.dataout='FTD:'+fnn
    fittp.g
    os.unsetenv('FTD')
    #zap the image
    outUV.Zap(err)
    del outUV
    #return outUV

def KATSplatandUVFITS(inUV, filename, outDisk, err, logfile=""):
    """
    Splat the highest SN table into inUV and write it out as a uvfits file
    """

    #Make copy of inUV
    tempUV = UV.newPAUV("TEMP UV DATA", "TEMP", "AV", 1, 1, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating UV data")
    # Clone
    UV.PCopy(inUV, tempUV, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error cloning UV data")
    UV.PCopyTables (inUV, tempUV, ["AIPS HI", "AIPS SL", "AIPS PL"], ["AIPS AN", "AIPS FQ", "AIPS SU"], err)
    # Generate an empty CL Table
    print("Create Initial CL table\n")
    UV.PTableCLGetDummy(tempUV, tempUV, 1, err, solInt=4.)
    tempUV.Open(UV.READONLY,err)
    tempUV.Close(err)

    # CLCal SN to CL
    EVLAApplyCal(tempUV,err,logfile=logfile)

    # Splattage
    splat = ObitTask.ObitTask('Splat')
    try:
        splat.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    splat.taskLog = logfile
    setname(tempUV,splat)
    splat.doCalib  = 2
    splat.gainUse  = 0
    splat.doBand   = 0
    splat.BPVer    = -1
    splat.BIF      = 1
    splat.EIF      = 0
    splat.BChan    = 1
    splat.EChan    = 0
    splat.flagVer  = -1
    splat.FreqID   = 0
    splat.timeAvg  = 0.
    splat.avgFreq  = 0
    splat.chAvg    = -1
    splat.corrType = 0
    splat.Compress = False
    splat.outName  = splat.inName
    splat.outClass = splat.inClass
    splat.outDisk  = splat.inDisk
    newseq = splat.inSeq + 1
    splat.outSeq   = newseq
    splat.g

    # Get rid of original data
    tempUV.Zap(err)
    # Open splatted data
    tempUV = UV.newPAUV("TEMP UV DATA", "TEMP", "AV", 1, newseq, True, err)

    # Put splatted data to disk in uvfits file
    KATUVFITS(tempUV,filename, outDisk, err, logfile=logfile)
    tempUV.Zap(err)
    return


def EVLAUVFITSTab(inUV, filename, outDisk, err, \
              exclude=["AIPS HI", "AIPS AN", "AIPS FQ", "AIPS SL", "AIPS PL"], \
                  include=[], logfile=""):
    """
    Write Tables on UV data as FITS file

    Write Tables from a UV data set (but no data) as a FITAB format file
    History written to header

    * inUV       = UV data to copy
    * filename   = name of FITS file, any whitespace characters replaced with underscore
    * outDisk    = FITS directory number
    * err        = Python Obit Error/message stack
    * exclude    = List of table types NOT to copy
      NB: "AIPS HI" isn't really a table and gets copied anyway
    * include    = List of table types to copy (FQ, AN always done )
      Exclude has presidence over include

    returns FITS UV data object
    """
    ################################################################
    mess =  "Write Tables to FITS UV data "+filename+" on disk "+str(outDisk)
    printMess(mess, logfile)
    # Checks
    if not UV.PIsA(inUV):
        raise TypeError("inUV MUST be a Python Obit UV")
    if not OErr.OErrIsA(err):
        raise TypeError("err MUST be an OErr")
    #
    # Deblank filename
    fn = re.sub('\s','_',filename)
    # Set output
    outUV = UV.newPFUV("FITS UV DATA", fn, outDisk, False, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error creating FITS data")
    # Clone
    UV.PClone (inUV, outUV, err)
    if err.isErr:
        OErr.printErrMsg(err, "Error cloning UV data to FITS")
    # Copy back to header
    inHistory  = History.History("inhistory",  outUV.List, err)
    outHistory = History.History("outhistory", outUV.List, err)
    # Add history
    outHistory.Open(History.READWRITE, err)
    outHistory.TimeStamp(" Start Obit uvTabSave",err)
    outHistory.WriteRec(-1,"uvTabSave / FITS file "+fn+" disk "+str(outDisk),err)
    outHistory.Close(err)
    History.PCopy2Header (inHistory, outHistory, err)
    OErr.printErrMsg(err, "Error with history")
    # zap table
    outHistory.Zap(err)
    # Copy Tables
    UV.PCopyTables (inUV, outUV, exclude, include, err)
    return outUV  # return new object
    # end EVLAUVFITSTab

def KATDropChan(uv, BChDrop, EChDrop, err, timeav=-1, flagVer=2, \
                 logfile='', check=False, debug=False):
    """
    Drop end channels from each spectrum (IF)

    Returns 0=OK, else failed
    * uv       = UV data object to copy
    * BChDrop  = number of channels to drop from the beginning of each IF
    * EChDrop  = number of channels to drop from the end of each IF
    * flagVer  = flag table version
    * err      = Obit error/message stack
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################

#    if check:
#        return 0
#    if BChDrop>0:
#        UV.PFlag(uv,err,flagVer=flagVer, Chans=[1,max(1,BChDrop)], IFs=[1,0], \
#                 Reason="End Channels")
#    if EChDrop>0:
#        d     = uv.Desc.Dict
#        nchan = d["inaxes"][d["jlocf"]]
#        ch = nchan - EChDrop + 1
#        UV.PFlag(uv,err,flagVer=flagVer, Chans=[ch, nchan], IFs=[1,0], \
#                 Reason="End Channels")
#    OErr.printErrMsg(err, "Error Flagging")
    
    d     = uv.Desc.Dict
    nchan = d["inaxes"][d["jlocf"]]

    # Now splat the data
    splat=ObitTask.ObitTask("Splat")
    try:
        splat.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    splat.taskLog = logfile
    if not check:
        setname(uv,splat)
    splat.doCalib  = 0
    splat.gainUse  = -1
    splat.doBand   = 0
    splat.BPVer    = -1
    splat.BIF      = 1
    splat.EIF      = 0
    splat.BChan    = BChDrop
    splat.EChan    = nchan - EChDrop
    splat.flagVer  = flagVer
    splat.FreqID   = 0
    splat.timeAvg  = timeav
    splat.avgFreq  = 0
    splat.chAvg    = -1
    splat.corrType = 1   # include autocorrs
    splat.Compress = False
    splat.outName  = splat.inName
    splat.outClass = 'Cut'
    splat.outDisk  = splat.inDisk
    splat.outSeq   = splat.inSeq
    if debug:
        splat.i
        splat.debug = debug
    # Trap failure
    try:
        if not check:
            splat.g
            pass
    except Exception as exception:
        print(exception)
        mess = "Splat Failed retCode="+str(splat.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    # end splat
    
    outUV = UV.newPAUV("AIPS UV DATA", splat.outName, "Cut", splat.outDisk, splat.outSeq, True, err)
    if err.isErr:
        mess =  "Error getting channel cut data."
        printMess(mess, logfile)
        return None
    return outUV



    # end KATDropChan

def KATRecalcUV(uv, err, logfile = ""):
    """
    Recompute uvw coordinates using AIPS/Obit uvw calculator
    """
    mess = "Recomputing uvw coordinates"
    printMess(mess,logfile)
    uvfix=ObitTask.ObitTask("UVFix")
    try:
        uvfix.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    setname(uv,uvfix)
    uvfix.outName=uvfix.inName
    uvfix.outClass="UVFix"
    uvfix.outDisk=uvfix.inDisk
    uvfix.outSeq=uvfix.inSeq

    # Trap failure
    try:
            uvfix.g
            pass
    except Exception as exception:
        print(exception)
        mess = "UVFix Failed retCode="+str(uvfix.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    # end splat

    outUV = UV.newPAUV("AIPS UV DATA", uvfix.outName, uvfix.outClass, uvfix.outDisk, uvfix.outSeq, True, err)
    if err.isErr:
        mess =  "Error getting uvw corrected data."
        printMess(mess, logfile)
        return None
    uv.Zap(err)
    return outUV


def EVLAMedianFlag(uv, target, err, \
                       flagTab=2, flagSig=10.0, alpha=0.5, timeWind=2.0, \
                       doCalib=0, gainUse=0, doBand=0, BPVer=0, flagVer=-1, \
                       avgTime=0, avgFreq=0, chAvg=1, \
                       check=False, debug = False, \
                       nThreads=1, noScrat=[], logfile = ""):
    """
    Does Median window flagging

    Flag data based on deviations from a running median
    See documentation for task MednFlag for details
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to flag
    * target   = Target source name or list of names, blank = all
    * err      = Obit error/message stack
    * flagTab  = Output Flagging table version
    * flagSig  = Flagging level (sigma)
    * alpha    = Smoothing parameter
    * timeWind = Averaging window (min)
    * doCalib  = Apply calibration table
    * gainUse  = CL/SN table to apply
    * doBand   = If >0.5 apply bandpass cal.
    * BPVer    = Bandpass table version
    * flagVer  = Input Flagging table version
    * avgTime  = preaveraging time (min)
    * avgFreq  = 1=>avg chAvg chans, 2=>avg all chan, 3=> avg chan and IFs
    * chAvg    = number of channels to average
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * nThreads = Number of threads to use
    * noScrat  = list of disks to avoid for scratch files
    * logfile  = Log file for task
    """
    ################################################################
    mess =  "Median Window flagging"
    printMess(mess, logfile)
    medn=ObitTask.ObitTask("MednFlag")
    try:
        medn.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    setname(uv,medn)
    if type(target)==list:
        medn.Sources=target
    else:
        medn.Sources=[target]
    medn.flagTab  = flagTab
    medn.flagSig  = flagSig
    medn.alpha    = alpha
    medn.timeWind = timeWind
    medn.doCalib  = doCalib
    medn.gainUse  = gainUse
    medn.doBand   = doBand
    medn.BPVer    = BPVer
    medn.avgTime  = avgTime
    medn.avgFreq  = avgFreq
    medn.chAvg    = chAvg
    medn.flagVer  = flagVer
    medn.nThreads = nThreads
    medn.taskLog  = logfile
    medn.noScrat  = noScrat
    medn.debug    = debug
    #bombaroonie = BombsAwayWithCurtisLemay # DEBUG
    if debug:
        medn.i
    # Trap failure
    try:
        if not check:
            medn.g
    except Exception as exception:
        print(exception)
        mess = "Median flagging Failed retCode="+str(medn.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAMedianFlag

def EVLAQuack(uv, err, \
                  Stokes = " ", BIF=1, EIF=0, Sources=[], FreqID=0, \
                  subA=0, timeRange=[0.,0.], Antennas=[], flagVer=2, \
                  check=False, debug = False, \
                  begDrop=0.0, endDrop=0.0, Reason="Quack", logfile = ""):
    """
    Flags beginning and end of each scan

    Trim start and end of each selected scan,
    nothing done if begDrop=endDrop=0.0
    See documentation for task Quack for details
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to flag
    * err      = Obit error/message stack
    * Stokes   = Limit flagging by Stokes
    * BIF      = Limit flagging to BIF-EIF
    * EIF      = Limit flagging
    * Sources  = Sources selected
    * subA     = Subarray number 0=>all
    * FreqID   = Freq. ID to flag. -1=>all
    * timeRange= Time range to process
    * Antennas = List of antennas to include
    * flagVer  = Flag table version, 0 => highest
    * begDrop  = Time (min) to drop from beginning
    * endDrop  = Time (min) to drop from end
    * Reason   = Reason (max 24 char.)
    * logfile  = Log file for task
    """
    ################################################################
    # Anything to do?
    if (begDrop<=0) and (endDrop<=0):
        return 0

    mess =  "Quack data"
    printMess(mess, logfile)
    quack=ObitTask.ObitTask("Quack")
    try:
        quack.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass

    if not check:
        setname(uv, quack)
    quack.Stokes    = Stokes
    quack.BIF       = BIF
    quack.EIF       = EIF
    quack.Sources   = Sources
    quack.subA      = subA
    quack.FreqID    = FreqID
    quack.timeRange = timeRange
    quack.Antennas  = Antennas
    quack.flagVer   = flagVer
    quack.begDrop   = begDrop
    quack.endDrop   = endDrop
    quack.Reason    = Reason
    quack.taskLog   = logfile
    if debug:
        quack.i
        quack.debug = debug
    # Trap failure
    try:
        if not check:
            quack.g
    except Exception as exception:
        print(exception)
        mess = "Quack Failed retCode= "+str(quack.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAQuack

def EVLAShadow(uv, err, shadBl=25.0, flagVer=2, \
                  check=False, debug=False, logfile = ""):
    """
    Flags antennas shadowed by others

    See documentation for task AIPSD/UVFLG for details
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to flag
    * err      = Obit error/message stack
    * shadBL   = Minimum shadowing baseline (m)
    * flagVer  = Flag table version, 0 => highest
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * logfile  = Log file for task
    """
    ################################################################
    mess =  "Shadow flag data"
    printMess(mess, logfile)
    uvflg=AIPSTask.AIPSTask("uvflg")
    try:
        uvflg.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass

    if not check:
        setname(uv, uvflg)
    uvflg.opcode    = "FLAG"
    uvflg.aparm[5]  = shadBl
    uvflg.outfgver  = flagVer
    uvflg.reason    = "Shadowed"
    uvflg.logFile   = logfile
    uvflg.msgkill   = 5        # Suppress blather
    if debug:
        uvflg.i
    # Trap failure
    try:
        if not check:
            uvflg.g
    except Exception as exception:
        print(exception)
        mess = "UVFLG Failed retCode= "+str(uvflg.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAShadow

def KAT7Elev(uv, err, minelev=15.0, flagVer=2, \
                  check=False, debug=False, logfile = ""):
    """
    Flags sources lower than given elevation

    See documentation for task AIPSD/UVFLG for details
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to flag
    * err      = Obit error/message stack
    * minelev  = Minimum elevation to keep
    * flagVer  = Flag table version, 0 => highest
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * logfile  = Log file for task
    """
    ################################################################
    mess =  "Elevation flag data"
    printMess(mess, logfile)
    uvflg=AIPSTask.AIPSTask("uvflg")
    try:
        uvflg.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass

    if not check:
        setname(uv, uvflg)
    uvflg.opcode    = "FLAG"
    uvflg.aparm[1]  = 0.0
    uvflg.aparm[2]  = minelev
    uvflg.outfgver  = flagVer
    uvflg.reason    = "Elevation"
    uvflg.logFile   = logfile
    uvflg.msgkill   = 5        # Suppress blather
    if debug:
        uvflg.i
    # Trap failure
    try:
        if not check:
            uvflg.g
    except Exception as exception:
        print(exception)
        mess = "UVFLG Failed retCode= "+str(uvflg.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end KAT7ElevFlag


def EVLAAutoFlag(uv, target, err, \
                     doCalib=0, gainUse=0, doBand=0, BPVer=0, flagVer=-1, \
                     flagTab=2, VClip=[0.0,0.0], IClip=[0.0,0.0], XClip=[0.0,0.0], minAmp=0.0, \
                     RMSClip=[0.0,0.0], RMSAvg=0.0, maxBad=0.25 ,timeAvg=1.0, \
                     doFD=False, FDmaxAmp=0.0, FDmaxV=0.0, FDwidMW=5, FDmaxRMS=[0.0,0.0], \
                     FDmaxRes=6.0, FDmaxResBL=6.0,  FDbaseSel=[0, 0, 0, 0], \
                     nThreads=1, check=False, debug=False, logfile = ""):
    """
    Does Automated flagging

    Flag data based on any of a number of criteria
    See documentation for task AutoFlag for details
    Returns task error code, 0=OK, else failed

    * uv         = UV data object to flag
    * target     = Target source name or list of names, blank = all
    * err        = Obit error/message stack
    * doCalib    = Apply calibration table
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply bandpass cal.
    * BPVer      = Bandpass table version
    * flagVer    = Input Flagging table version
    * flagTab    = Output Flagging table version
    * VClip      = If > 0.0 VPol clipping level
    * IClip      = If > 0.0 IPol clipping level
    * XClip      = If > 0.0 Cross-pol clipping level
    * minAmp     = Min flux for IClip flagging
    * RMSClip    = Abs and fractional clip levels for
      Time domain RMS filtering
    * RMSAvg     = Max RMS/Avg for time domain RMS filtering
    * maxBad     = Maximum fraction of baselines for
      correlator or antenna to be
      flagged before all are flagged
    * timeAvg    = Flagging interval (min)
    * doFD       = do frequency domain editing?
    * FDmaxAmp   = Maximum average amplitude
    * FDmaxV     = Maximum average VPol amp
    * FDwidMW    = Width of the median window
    * FDmaxRMS   = Channel RMS limits
    * FDmaxRes   = Max. residual flux in sigma
    * FDmaxResBL = Max. baseline residual
    * FDbaseSel  =  Channels for baseline fit (start, end, increment, IF)
    * nThreads = Number of threads to use
    * check      = Only check script, don't execute tasks
    * debug      = Run tasks debug, show input
    * logfile    = Log file for task
    """
    ################################################################
    # Anything requested?
    if (IClip==None or IClip[0]==0.) and (VClip==None or VClip[0]==0.) and \
       (XClip==None or XClip[0]==0.) and (RMSClip==None or RMSClip[0]==0.) and \
       (doFD==False) and (minAmp==0.0) and (RMSAvg==0.0): \
       return 0

    mess =  "AutoFlag data"
    printMess(mess, logfile)
    af=ObitTask.ObitTask("AutoFlag")
    try:
        af.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv,af)
    if type(target)==list:
        af.Sources=target
    else:
        af.Sources=[target]
    af.flagTab    = flagTab
    af.flagVer    = flagVer
    af.doCalib    = doCalib
    af.gainUse    = gainUse
    af.doBand     = doBand
    af.BPVer      = BPVer
    af.VClip      = VClip
    af.IClip      = IClip
    if  "XClip" in af.__dict__:
        af.XClip      = XClip
    af.minAmp     = minAmp
    af.RMSClip    = RMSClip
    af.RMSAvg     = RMSAvg
    af.maxBad     = maxBad
    af.timeAvg    = timeAvg
    af.doFD       = doFD
    af.FDmaxAmp   = FDmaxAmp
    af.FDmaxV     = FDmaxV
    af.FDwidMW    = FDwidMW
    af.FDmaxRMS   = FDmaxRMS
    af.FDmaxRes   = FDmaxRes
    af.FDmaxResBL = FDmaxResBL
    af.FDbaseSel  = FDbaseSel
    af.nThreads   = nThreads
    af.taskLog    = logfile
    if debug:
        af.i
        af.debug = debug
    # Trap failure
    try:
        if not check:
            af.g
    except Exception as exception:
        print(exception)
        mess = "AutoFlag Failed retCode="+str(af.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAAutoFlag

def EVLAPACor(uv, err, CLver=0, FreqID=0,\
              logfile='', check=False, debug=False):
    """
    Make parallactic angle correction

    Updates CL CLver, if only one, a new one (CL 2) is copied
    Returns task error code, 0=OK, else failed

    * uv         = UV data object
    * err        = Python Obit Error/message stack
    * CLver      = Cl version to update, 0=> highest
    * FreqID     = Frequency group identifier
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input
    """
    ################################################################
    # Don't bother if not full polarization
    d     = uv.Desc.Dict
    nstoke = d["inaxes"][d["jlocs"]]
    if nstoke<4:
        mess = "Skip Parallactic angle corrections - not full stokes"
        printMess(mess, logfile)
        return 0
    # Don't bother if linear feeds
    stok0 = d["crval"][d["jlocs"]]
    if stok0<-4:
        mess = "Skip Parallactic angle corrections - Linear feeds"
        printMess(mess, logfile)
        return 0

    # Which CL?
    iCLver = CLver
    if iCLver<=0 and not check:
        # Open and close image to sync with disk
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        iCLver = uv.GetHighVer("AIPS CL")
    # If iCLver==1, copy to 2 first
    if iCLver==1 and not check:
        oCLver = iCLver+1
    else:
        oCLver = iCLver

    mess = "Parallactic angle corrections made to CL "+str(oCLver)
    printMess(mess, logfile)

    clcor = ObitTask.ObitTask("CLCor")
    try:
        clcor.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv,clcor)
    clcor.corMode     = "PANG"
    clcor.calIn       = iCLver
    clcor.calOut      = oCLver
    clcor.CLCParm[0]  = 1.0
    clcor.FreqID      = FreqID
    clcor.taskLog     = logfile
    if debug:
        clcor.i
        clcor.debug = debug
    # Trap failure
    try:
        if not check:
            clcor.g
    except Exception as exception:
        print(exception)
        mess = "CLCor Failed "
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAPACor

def KATGetCalModel(uv, parms, fileroot, err, logFile='', sefd=1000., check=False, debug=False, noScrat=[], nThreads=1):
    """
    Make an image of the phase calibrators and make a CC
    table model that can be used as a calibrator model.

    * uv    = uv data to image
    * parms = full set of input parameters
    * err   = Python Obit Error
    
    returns: retcode (1=fail)
             parms   (updated to include calibrator model information)
    
    """

    retCode=0

    user = OSystem.PGetAIPSuser()

    uvcop=AIPSTask.AIPSTask("uvcop")
    setname(uv, uvcop)
    uvcop.userno = user
    uvcop.outname = "UV COPY"
    uvcop.outclass = "UVDATA"
    uvcop.outdisk = parms["disk"]
    uvcop.outseq = parms["seq"]
    uvcop.bchan = 0
    uvcop.echan = 0
    uvcop.flagver = 0
    try:
        uvcop.g
    except Exception as exception:
        print("Unable to Copy UV data (userno: %i)" % uvcop.userno)
        return 1, parms

    # Get uv_alt
    uv_alt = UV.newPAUV("COPY OF UV DATA", "UV COPY", "UVDATA", parms["disk"], parms["seq"], True, err)

    clist = [PCal["Source"] for PCal in parms["PCals"]]

    # Bandpass calibration
    if parms["doBPCal"] and parms["BPCals"]:
        retCode = KATBPCal(uv_alt, parms["BPCals"], err, noScrat=noScrat, solInt1=parms["bpsolint1"], \
                            solInt2=parms["bpsolint2"], solMode=parms["bpsolMode"], \
                            BChan1=parms["bpBChan1"], EChan1=parms["bpEChan1"], \
                            BChan2=parms["bpBChan2"], EChan2=parms["bpEChan2"], ChWid2=parms["bpChWid2"], \
                            doCenter1=parms["bpDoCenter1"], refAnt=parms["refAnt"], \
                            UVRange=parms["bpUVRange"], doCalib=-1, gainUse=0, flagVer=2, doPlot=False, \
                            nThreads=nThreads, logfile=logFile, check=check, debug=debug)
        if retCode!=0:
            raise RuntimeError("Error in Bandpass calibration")

    # Amp & phase Calibrate
    if parms["doAmpPhaseCal"]:
        retCode = KATCalAP (uv_alt, [], parms["ACals"], err, PCals=parms["PCals"], 
                             doCalib=-1, doBand=1, BPVer=1, flagVer=2, \
                             BChan=parms["ampBChan"], EChan=parms["ampEChan"], \
                             solInt=parms["solInt"], solSmo=parms["solSmo"], ampScalar=parms["ampScalar"], \
                             doAmpEdit=parms["doAmpEdit"], ampSigma=parms["ampSigma"], \
                             ampEditFG=parms["ampEditFG"], \
                             doPlot=False, plotFile='',  refAnt=parms["refAnt"], \
                             nThreads=nThreads, noScrat=noScrat, logfile=logFile, check=check, debug=debug)
        if retCode!=0:
            raise RuntimeError("Error calibrating")
    
    #Flag
    if parms["doAutoFlag"]:
        retCode = EVLAAutoFlag (uv_alt, clist, err, flagVer=2, \
                                    doCalib=2, gainUse=0, doBand=2, BPVer=1,  \
                                    IClip=parms["IClip"], minAmp=parms["minAmp"], timeAvg=parms["timeAvg"], \
                                    doFD=parms["doAFFD"], FDmaxAmp=parms["FDmaxAmp"], FDmaxV=parms["FDmaxV"], \
                                    FDwidMW=parms["FDwidMW"], FDmaxRMS=parms["FDmaxRMS"], \
                                    FDmaxRes=parms["FDmaxRes"],  FDmaxResBL=parms["FDmaxResBL"], \
                                    FDbaseSel=parms["FDbaseSel"], \
                                    nThreads=nThreads, logfile=logFile, check=check, debug=debug)
        if retCode!=0:
            raise  RuntimeError("Error in AutoFlag")
    
    # Calibrate and average data
    if parms["doCalAvg"]:
        retCode = KATCalAvg (uv_alt, "AVG_T", parms["seq"], parms["CalAvgTime"], err, \
                              flagVer=2, doCalib=2, gainUse=0, doBand=2, BPVer=1, doPol=False, \
                              avgFreq=parms["avgFreq"], chAvg=parms["chAvg"], \
                              BChan=1, EChan=parms["selChan"] - 1, doAuto=parms["doAuto"], \
                              BIF=parms["CABIF"], EIF=parms["CAEIF"], Compress=parms["Compress"], \
                              nThreads=nThreads, logfile=logFile, check=check, debug=debug)
        if retCode!=0:
           raise  RuntimeError("Error in CalAvg")

    # Get calibrated/averaged data
    if not check:
        uv_alt_av = UV.newPAUV("AIPS UV DATA", "UV COPY", "AVG_T", \
                            parms["disk"], parms["seq"], True, err)
        if err.isErr:
            OErr.printErrMsg(err, "Error creating cal/avg AIPS data")

    uv_alt.Zap(err)
    NewPCals=[]
    # Loop over calibrators
    for cal in parms["PCals"]:
        source = cal["Source"]
        # Get the flux of the calibrators
        suinfo = EVLAGetTimes(uv_alt_av, source, err, logfile=logFile, check=check, debug=debug)
        iflux=suinfo["IFlux"][0]
        fluxlim=max(0.01*iflux,0.1)
        
        # Image the calibrators down to 5% of the peak with few CC's and high gain to get a model.
        imageret=KATImageTargets (uv_alt_av, err, Sources=source, seq=parms["seq"], sclass="MODEL", CCVer=1, CGain=0.1,\
                             doCalib=-1, doBand=-1,  flagVer=-1, doPol=parms["doPol"], PDVer=parms["PDVer"],  \
                             Stokes=parms["Stokes"], FOV=1.5, OutlierArea=1.5, Robust=-2.0, Niter=300, \
                             CleanRad=None, minFlux=fluxlim, OutlierSize=parms["OutlierSize"], \
                             xCells=parms["xCells"], yCells=parms["yCells"], Reuse=parms["Reuse"], minPatch=parms["minPatch"], \
                             maxPSCLoop=parms["maxPSCLoop"], minFluxPSC=fluxlim, noNeg=parms["noNeg"], \
                             solPInt=parms["solPInt"], solPMode=parms["solPMode"], solPType=parms["solPType"], \
                             maxASCLoop=2, minFluxASC=fluxlim, nx=parms["nx"], ny=parms["ny"], \
                             solAInt=parms["solAInt"], solAMode=parms["solAMode"], solAType=parms["solAType"], \
                             avgPol=parms["avgPol"], avgIF=parms["avgIF"], minSNR = parms["minSNR"], refAnt=parms["refAnt"], \
                             do3D=parms["do3D"], BLFact=parms["BLFact"], BLchAvg=parms["BLchAvg"], \
                             doMB=parms["doMB"], norder=parms["MBnorder"], maxFBW=parms["MBmaxFBW"], \
                             PBCor=parms["PBCor"],antSize=parms["antSize"], sefd=sefd, \
                             nTaper=parms["nTaper"], Tapers=parms["Tapers"], \
                             nThreads=nThreads, noScrat=noScrat, logfile=logFile, check=check, debug=False)

        # Update the model parameters with the output
        aipsimname=source[0:12]
        oclass="IODEL"
        oseq=parms["seq"]
        # Test if image exists
        exists = AIPSDir.PTestCNO(parms["disk"], user, aipsimname, oclass, "MA", oseq, err)
        
        if exists > 0 and imageret == 0:       
            x = Image.newPAImage("out_model", aipsimname, oclass, parms["disk"], oseq, True, err)
            outfile = fileroot + '_'+source+'_model.fits'
            xf = KATImFITS (x, outfile, 0, err, logfile=logFile)
            EVLAAddOutFile(outfile, 'M'+source, 'Model image of '+ source)
        
            cal['CalDataType']='AIPS'
            cal['CalName']=aipsimname
            cal['CalClass']=oclass
            cal['CalSeq']=oseq
            cal['CalDisk']=parms['disk']
            cal['CalNfield']=1
            cal['CalBComp']=[1]
            cal['CalEComp']=[0]
            cal['CalCmethod']='DFT'
            cal['CalCCVer']=0
            cal['CalFlux']=fluxlim
            cal['CalModelFlux']=0
            cal['CalCModel']='COMP'
            
        NewPCals.append(cal)

    uv_alt_av.Zap(err)
    # Fix PCals array
    parms["PCals"]=NewPCals

    NewDCals=[]
    # Fix DCals Array
    for dcal in parms["DCals"]:
        newcal=dcal
        for pcal in parms["PCals"]:
            if dcal["Source"] == pcal["Source"]:
                newcal=pcal
        NewDCals.append(newcal)
    
    parms["DCals"] = NewDCals

    return retCode,parms 

def EVLADelayCal(uv,DlyCals,  err, solInt=0.5, smoTime=10.0, BChan=1, EChan=0, \
                     timeRange=[0.,0.], FreqID=1, doCalib=-1, gainUse=0, minSNR=5.0, \
                     refAnts=[0], doBand=-1, BPVer=0, flagVer=-1, doTwo=True, doZeroPhs=False, \
                     doAvgIF=False, doAvgPol=False, \
                     doPlot=False, plotFile="./DelayCal.ps", \
                     nThreads=1, noScrat=[], logfile='', check=False, debug=False):
    """
    Group delay calibration

    Determine delay corrections from a list of calibrators
    Solutions optionally smoothed to smoTime
    Apply this SN table to the highest CL table writing a new CL table (Obit/CLCal)
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to calibrate
    * DlyCals    = List of delay calibrators possibly with model
    * err        = Python Obit Error/message stack
    * BChan      = First (1-rel channel to include
    * EChan      = Highest channel to include
    * timeRange  = timerange of data to use
    * solInt     = Calib solution interval (min)
    * smoTime    = Smoothing time applied to SN table (hr) if >0.0
    * FreqID     = Frequency group identifier
    * minSNR     = minimum acceptable SNR in Calib
    * refAnts    = List of reference antennas
    * doCalib    = Apply calibration table
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply bandpass cal.
    * BPVer      = Bandpass table version
    * flagVer    = Input Flagging table version
    * doTwo      = If True, use one and two baseline combinations
      for delay calibration, else only one baseline
    * doAvgIF    = Average the IF during delay calibration
    * doAvgPol   = Average the polarizations
    * doPlot     = If True make plots of SN gains
    * plotFile   = Name of postscript file for plots
    * nThreads   = Max. number of threads to use
    * noScrat    = list of disks to avoid for scratch files
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input
    """
    ################################################################
    mess = "Determine parallel hand group delays"
    printMess(mess, logfile)

    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)

    # Set output (new) SN table
    SNver = uv.GetHighVer("AIPS SN")+1

    calib = ObitTask.ObitTask("Calib")
    try:
        calib.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    OK = False   # Must have some work
    calib.taskLog  = logfile
    if not check:
        setname(uv,calib)
    calib.flagVer   = flagVer
    calib.timeRange = timeRange
    calib.doCalib   = doCalib
    calib.gainUse   = gainUse
    calib.doBand    = doBand
    calib.BPVer     = BPVer
    calib.solMode   = "DELA"
    calib.solType   = "   "
    calib.solInt    = solInt
    calib.minSNR    = 5.0
    calib.refAnts   = refAnts
    calib.solnVer   = SNver
    calib.noScrat   = noScrat
    calib.nThreads  = nThreads
    calib.doTwo     = True
    calib.avgIF     = doAvgIF
    calib.avgPol    = doAvgPol
    # Loop over calibrators
    for DlyCal in DlyCals:
        calib.Sources[0]= DlyCal["Source"]
        calib.DataType2 = DlyCal["CalDataType"]
        calib.in2File   = DlyCal["CalFile"]
        calib.in2Name   = DlyCal["CalName"]
        calib.in2Class  = DlyCal["CalClass"]
        calib.in2Seq    = DlyCal["CalSeq"]
        calib.in2Disk   = DlyCal["CalDisk"]
        calib.nfield    = DlyCal["CalNfield"]
        calib.CCVer     = DlyCal["CalCCVer"]
        calib.BComp     = DlyCal["CalBComp"]
        calib.EComp     = DlyCal["CalEComp"]
        calib.Cmethod   = DlyCal["CalCmethod"]
        calib.Cmodel    = DlyCal["CalCmodel"]
        calib.Flux      = DlyCal["CalFlux"]
        calib.Alpha     = 0.0
        calib.modelFlux = DlyCal["CalModelFlux"]
        calib.modelPos  = DlyCal["CalModelPos"]
        calib.modelParm = DlyCal["CalModelParm"]
        if debug:
            calib.prtLv =6
            calib.i
            calib.debug = debug
        # Trap failure
        try:
            mess = "Run Calib on "+calib.Sources[0]
            printMess(mess, logfile)
            if not check:
                calib.g
        except Exception as exception:
            print(exception)
            mess = "Calib Failed retCode= "+str(calib.retCode)+" Source "+calib.Sources[0]
            printMess(mess, logfile)
            #return None  # Allow some to fail
        else:
            OK = True
    # End loop over calibrators
    # Something work?
    if not OK:
        printMess("All Delay calibration failed", logfile)
        return 1

    # Open/close UV to update header
    uv.Open(UV.READONLY,err)
    uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        printMess("Update UV header failed", logfile)
        return 1
    SNver = uv.GetHighVer("AIPS SN")

    # Zero phases?
    if doZeroPhs:
        sncor = ObitTask.ObitTask("SNCor")
        try:
            sncor.userno     = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        if not check:
            setname(uv, sncor)
        sncor.solnVer    = SNver
        sncor.corMode    = 'ZPHS'
        sncor.timeRange  = timeRange
        sncor.taskLog    = logfile
        sncor.debug      = debug
        if debug:
            sncor.i
        mess = "EVLADelayCal: SNCor: Zero phase in SN "+str(sncor.solnVer)
        printMess(mess, logfile)
        # Trap failure
        try:
            if not check:
                sncor.g
        except Exception as exception:
            print(exception)
            mess = "SNCor Failed retCode="+str(sncor.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
    # End SNCor

    # Smooth if requested
    if smoTime>0.0:
        snsmo = ObitTask.ObitTask("SNSmo")
        try:
            snsmo.userno     = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        if not check:
            setname(uv, snsmo)
        snsmo.solnIn     = SNver
        snsmo.solnOut    = SNver+1
        snsmo.smoType    = 'VLBI'
        snsmo.smoFunc    = 'MWF '
        snsmo.smoParm    = [smoTime,smoTime,smoTime,smoTime,smoTime]
        # Clip ay 0.5 nsec from median
        snsmo.clipSmo    = [5*smoTime,5*smoTime,5*smoTime,5*smoTime,5*smoTime]
        snsmo.clipParm   = [0.0, 0.0, 0.0, 0.5, 0.5]
        snsmo.doBlank    = True
        snsmo.refAnt     = refAnts[0]
        snsmo.taskLog    = logfile
        snsmo.debug      = debug
        #snsmo.debug     = True  # DEBUG
        #bombaroonie     = BombsAwayWithCurtisLemay # DEBUG
        if debug:
            snsmo.i
        mess = "EVLADelayCal: SNSmo SN "+str(snsmo.solnIn)+" to "+str(snsmo.solnOut)
        printMess(mess, logfile)
        # Trap failure
        try:
            if not check:
                snsmo.g
        except Exception as exception:
            print(exception)
            mess = "SNSmo Failed retCode="+str(snsmo.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
    # End SNSmo

    # Open/close UV to update header
    uv.Open(UV.READONLY,err)
    uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1
    SNver = uv.GetHighVer("AIPS SN")
    # Plot fits?
    if doPlot:
        retCode = EVLAPlotTab(uv, "SN", SNver, err, nplots=6, optype="DELA", \
                                  logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode

        retCode = EVLAWritePlots (uv, 1, 0, plotFile, err, \
                                  plotDesc="Group delay plots", \
                                  logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode

    # end SN table plot
    # Apply to CL table
    retCode = EVLAApplyCal(uv, err, maxInter=1440.0, logfile=logfile, check=check,debug=debug)
    if retCode!=0:
        return retCode
    
    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    return 0
    # end EVLADelayCal

def KATCalAP(uv, target, ACals, err, \
              PCals=None, FQid=0, calFlux=None, \
              doCalib=-1, gainUse=0, doBand=0, BPVer=0, flagVer=-1, \
              BChan=1, EChan=1, avgPol=False, \
              solnver=0, solInt=10.0/60.0, solSmo=0.0, nThreads=1, refAnt=0, ampScalar=False, \
              doAmpEdit=False, ampSigma=50, flagFail=False, ampEditFG=-1, \
              doPlot=False, plotFile="./APCal.ps", \
              check=False, debug = False, noScrat=[], logfile = ""):
    """
    Basic Amplitude and phase cal for KAT-7 data

    Amplitude calibration can be based either on a point flux
    density or a calibrator model.
    An attempt is made to use the setjy.OPType="CALC" option.
    Optional editing/flagging on the basis of deviant amplitudes.
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to calibrate
    * target   = Target source name or list of names to calibrate
    * avgPol   = Average polarisations in calibration?
    * ACals    = List of Amp calibrators possibly with model
    * err      = Obit error/message stack
    * PCals    = if given, List of phase calibrators possibly with model
    * FQid     = Frequency Id to process, 0=>any
    * BChan    = First (1-rel channel to include
    * EChan    = Highest channel to include
    * doCalib  = Apply calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * doBand   = If >0.5 apply previous bandpass cal.
    * BPVer    = previous Bandpass table (BP) version
    * flagVer  = Flagging table to apply
    * solnver  = output SN table version (+1 if smooth), 0=>new
    * solInt   = solution interval (min)
    * solSmo   = if solSmo<solInt smooth amp solutions to solSmo
    * nThreads = Number of threads to use
    * refAnt   = Reference antenna
    * ampScalar= If true, scalar average data in calibration?
    * doAmpEdit= Edit/flag on the basis of amplitude solutions
    * ampSigma = Multiple of median RMS about median gain to clip/flag
                 Should be fairly large
    * ampEditFG= FG table to add flags to, <=0 -> no FG entries
    * flagFail = If True enter times for failed solutions if FG  mpEditFG
    * doPlot   = If True make plots of solutions
    * plotFile = Name of postscript file for plots
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * noScrat  = list of disks to avoid for scratch files
    * logfile  = Log file for tasks
    """
    ################################################################
    mess =  "Amplitude and phase calibration"
    printMess(mess, logfile)
    solnVer2 = None

    # Run SetJy
    setjy = ObitTask.ObitTask("SetJy")
    try:
        setjy.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    setjy.taskLog  = logfile
    if not check:
        setname(uv,setjy)
    OK = False   # Must have some work
    # Loop over calibrators
    OKAmpCals = []  # Calibrators SetJy is happy with
    BadAmpCals = [] # Calibrators SetJy is unhappy with
    for ACal in ACals:
        setjy.Sources[0] = ACal["Source"]
        if FQid:
            setjy.FreqID=FQid
        #Deal with 0408
        #if '0407' in ACal["Source"]:
        #    setjy.OPType="    "
        #    setjy.ZeroFlux[0] = ACal["CalFlux"]
        #else:
        setjy.OPType="CALC"
        setjy.ZeroFlux=[1.0,0.0,0.0,0.0]
        #ACal["CalFlux"]=0.0
        #if ACal["CalFlux"]>0.0:
        #    setjy.ZeroFlux[0] = ACal["CalFlux"]
        #else:
        #setjy.OPType="CALC"
        #setjy.ZeroFlux=[1.0,0.0,0.0,0.0]
        if debug:
            setjy.i
            setjy.debug = debug
        # Trap failure
        try:
            if not check:
                setjy.g
        except Exception as exception:
            print(exception)
            mess = "SetJy Failed retCode="+str(setjy.retCode)+" for "+setjy.Sources[0]
            printMess(mess, logfile)
            # return 1  # allow some failures
            BadAmpCals.append(setjy.Sources[0])
        else:
            OK = True
            OKAmpCals.append(setjy.Sources[0])
    # end loop over calibrators
    # Something work?
    if not OK:
        printMess("All Amplitude calibrators failed", logfile)
        return 1

    # output SN version
    if solnver<=0:
        # Open and close image to sync with disk
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        solnVer  = max(1,uv.GetHighVer("AIPS SN")+1)
    else:
        solnVer  = solnver

    # Phase cals and failed amp cals to 1.0
    callist = []
    for PCal in PCals:
        if PCal["Source"] not in OKAmpCals:
            callist.append(PCal["Source"])
    for cal in BadAmpCals:
        if cal not in OKAmpCals:
            callist.append(cal)
    if len(callist)>0:
        setjy.ZeroFlux=[1.0,0.0,0.0,0.0]
        setjy.OPType="REJY"
        #setjy.debug = True # DEBUG
        for cal in callist:
            setjy.Sources[0] = cal
            if debug:
                setjy.i
                setjy.debug = debug
            # Trap failure
            try:
                if not check:
                    setjy.g
            except Exception as exception:
                print(exception)
                mess = "SetJy Failed retCode="+str(setjy.retCode)
                printMess(mess, logfile)
                return 1
            else:
                pass

    # Calib on Amp cals
    calib = ObitTask.ObitTask("Calib")
    try:
        calib.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    calib.taskLog  = logfile
    if not check:
        setname(uv,calib)
    calib.flagVer  = flagVer
    calib.ampScalar= ampScalar
    calib.doCalib  = doCalib
    calib.gainUse  = gainUse
    calib.doBand   = doBand
    calib.BPVer    = BPVer
    calib.solMode  = "A&P"
    calib.solType  = "L1"
    calib.nThreads = nThreads
    calib.solInt   = solInt
    calib.refAnts  = [refAnt]
    calib.noScrat  = noScrat
    calib.solnVer  = solnVer
    calib.noNeg    = True
    calib.avgPol   = avgPol
    OK      = False   # Must have some work
    OKCals2 = []      # List of ones that worked
    # Loop over calibrators
    for ACal in ACals:
        calib.Sources[0]= ACal["Source"]
        calib.DataType2 = ACal["CalDataType"]
        calib.in2File   = ACal["CalFile"]
        calib.in2Name   = ACal["CalName"]
        calib.in2Class  = ACal["CalClass"]
        calib.in2Seq    = ACal["CalSeq"]
        calib.in2Disk   = ACal["CalDisk"]
        calib.nfield    = ACal["CalNfield"]
        calib.CCVer     = ACal["CalCCVer"]
        calib.BComp     = ACal["CalBComp"]
        calib.EComp     = ACal["CalEComp"]
        calib.Cmethod   = ACal["CalCmethod"]
        calib.Cmodel    = ACal["CalCmodel"]
        calib.modelPos  = ACal["CalModelPos"]
        calib.modelParm = ACal["CalModelParm"]
        if debug:
            calib.i
            calib.debug = True
        #calib.prtLv = 5
        # Trap failure
        try:
            mess = "Run Calib on "+calib.Sources[0]
            printMess(mess, logfile)
            if not check:
                calib.g
        except Exception as exception:
            print(exception)
            mess = "Calib Failed retCode= "+str(calib.retCode)+" Source "+calib.Sources[0]
            printMess(mess, logfile)
            #return 1  # allow some failures
        else:
            OK = True
            OKCals2.append(calib.Sources[0])
        # end calibration loop

    # Something work?
    if not OK:
        printMess("All amplitude calibrators failed", logfile)
        return 1

   # Setup CLCal
    clcal = ObitTask.ObitTask("CLCal")
    try:
        clcal.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    clcal.taskLog  = logfile
    ical = 0
    if not check:
        setname(uv,clcal)
    for ACal in ACals:
        clcal.calSour[ical] = ACal["Source"]
        ical += 1
    if not check:
        # Open and close image to sync with disk
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        clcal.calIn   = uv.GetHighVer("AIPS CL")
    else:
        clcal.calIn   = 1
    clcal.calOut    = clcal.calIn+1
    clcal.interMode = "2PT"
    #clcal.interMode = "SELF"  # DEBUG
    clcal.FreqID    = FQid

    # Calib on phase reference if given
    if PCals:
        OK = False   # Must have some work
        # Loop over calibrators
        for PCal in PCals:
            mess = "Consider Calib for "+PCal["Source"]
            printMess(mess, logfile)
            # Ignore if already done in ACals
            doIgnore = False
            for ACal in ACals:
                if ACal["Source"]==PCal["Source"]:
                    doIgnore = True
                    break
            if doIgnore:
                OK= True  # If we have A cals then its ok!
                mess = PCal["Source"]+" in ACal list"
                printMess(mess, logfile)
                continue
            calib.Sources[0]= PCal["Source"]
            calib.DataType2 = PCal["CalDataType"]
            calib.in2File   = PCal["CalFile"]
            calib.in2Name   = PCal["CalName"]
            calib.in2Class  = PCal["CalClass"]
            calib.in2Seq    = PCal["CalSeq"]
            calib.in2Disk   = PCal["CalDisk"]
            calib.nfield    = PCal["CalNfield"]
            calib.CCVer     = PCal["CalCCVer"]
            calib.BComp     = PCal["CalBComp"]
            calib.EComp     = PCal["CalEComp"]
            calib.Cmethod   = PCal["CalCmethod"]
            calib.Cmodel    = PCal["CalCmodel"]
            #calib.Flux      = PCal["CalFlux"]
            calib.Alpha     = PCal["CalModelSI"]
            #calib.modelFlux = PCal["CalModelFlux"]
            calib.modelPos  = PCal["CalModelPos"]
            calib.modelParm = PCal["CalModelParm"]
            
            if debug:
                calib.i
                calib.debug = debug
                calib.prtLv = 5
            # Trap failure
            try:
                mess = "Run Calib on "+calib.Sources[0]
                printMess(mess, logfile)
                if not check:
                    calib.g
            except Exception as exception:
                print(exception)
                mess = "Calib Failed retCode= "+str(calib.retCode)+" Source "+calib.Sources[0]
                printMess(mess, logfile)
                #return 1   # Allow some to fail
            else:
                OK = True
                OKCals2.append(calib.Sources[0])
        # end phase calibration loop
        # Something work?
        if not OK:
            printMess("All phase calibrators failed", logfile)
            return 1
    # end if phase cals

    solnVer2 = calib.solnVer
    # Smoothing?
    if solSmo>solInt:
        # Get list of calibrators
        smoList = []
        for ACal in ACals:
            smoList.append(ACal["Source"])
            if PCals:
                for PCal in PCals:
                    if PCal["Source"] not in smoList:
                        smoList.append(PCal["Source"])
            solnVer2 = solnVer+1
            snsmo=ObitTask.ObitTask("SNSmo")
            try:
                snsmo.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
            except Exception as exception:
                pass
            snsmo.taskLog  = logfile
            if not check:
                setname(uv,snsmo)
            snsmo.solnIn  = solnVer
            snsmo.solnOut = solnVer2
            snsmo.smoType = "AMPL"
            snsmo.smoFunc = "MWF"
            snsmo.refAnt  = refAnt
            snsmo.clipSmo = [24.]  # Clip wild amplitudes
            snsmo.clipParm= [100.0]
            mess = "Smooth SN "+str(snsmo.solnIn)+" to "+str(snsmo.solnOut)
            printMess(mess, logfile)
            if debug:
                snsmo.i
                snsmo.debug = debug
            # run on all sources for clipping then on individual cal.
            # Trap failure
            try:
                if not check:
                    snsmo.g
            except Exception as exception:
                print(exception)
                mess = "SNSmo Failed retCode="+str(snsmo.retCode)
                printMess(mess, logfile)
                return 1
            else:
                pass
            snsmo.clipSmo = [solSmo/60.0]
            snsmo.clipParm= [0.5]
            # Next time smooth
            snsmo.smoParm = [solSmo/60., solSmo/60.]
            snsmo.solnIn  = solnVer2
            snsmo.solnOut = solnVer2+1
            solnVer2     +=1
            # Loop over sources
            for s in smoList:
                snsmo.Sources[0] = s
                # Trap failure
                try:
                    if not check:
                        snsmo.g
                except Exception as exception:
                    print(exception)
                    mess = "SNSmo Failed retCode="+str(snsmo.retCode)
                    printMess(mess, logfile)
                    return 1
                else:
                    pass
        else:   # No smoothing
            solnVer2 = solnVer

    # Tell OKCals2 etc if debug
    if debug:
        mess = "OKCals2="+str(OKCals2)
        printMess(mess, logfile)
        mess = "OKAmpCals="+str(OKAmpCals)
        printMess(mess, logfile)
        mess = "BadAmpCals="+str(BadAmpCals)

    # GetJy to set flux density scale
    getjy = ObitTask.ObitTask("GetJy")
    try:
        getjy.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    getjy.taskLog  = logfile
    ical = 0; isou = 0
    if not check:
        setname(uv,getjy)
    for ACal in OKAmpCals:
        if ACal in OKCals2:
            getjy.calSour[ical] = ACal
            ical += 1
    # Amplitude calibrators with no flux
    for cal in BadAmpCals:
        if (cal not in getjy.calSour) and (cal not in getjy.Sources) \
               and (cal in OKCals2):
            getjy.Sources[isou] = cal
            isou += 1
    # Phase calibrators
    if PCals:
        for PCal in PCals:
            if (PCal["Source"] not in getjy.calSour) \
                   and (PCal["Source"] in OKCals2) \
                   and (PCal["Source"] not in getjy.Sources):
                getjy.Sources[isou] = PCal["Source"]
                isou += 1
    getjy.solnVer = solnVer2
    getjy.FreqID = FQid
    if debug:
        getjy.i
        getjy.debug = debug
    # Trap failure
    try:
        if not check:
            getjy.g
    except Exception as exception:
        print(exception)
        mess = "GetJy Failed retCode="+str(getjy.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass

    # enter flagged solutions in FG table?
    if flagFail:
        EVLAFlagFailSN(uv, 0, err, FGver=ampEditFG,  \
                      logfile=logfile, check=check, debug=debug)
        OErr.printErrMsg(err, "Error flagging data with failed solutions")
    # end flagFail

    # Clip/flag by deviant amplitudes?
    if doAmpEdit:
        EVLAEditSNAmp(uv, 0, err, sigma=ampSigma, FGver=ampEditFG,  \
                      logfile=logfile, check=check, debug=debug)
        OErr.printErrMsg(err, "Error clip/flag bad amplitudes")
    # end Amp edit

    # Plot gain corrections?
    if solnVer2==None:
        solnVer2 = solnVer
    if doPlot:
        # Amplitude corrections
        retCode = EVLAPlotTab(uv, "SN", solnVer2, err, nplots=6, optype="AMP ", \
                              logfile=logfile, check=check, debug=debug)
        # Phase corrections
        retCode = EVLAPlotTab(uv, "SN", solnVer2, err, nplots=6, optype="PHAS", \
                              logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode
        # R-L phase corrections
        retCode = EVLAPlotTab(uv, "SN", solnVer2, err, nplots=6, optype="PHAS", stokes="DIFF", \
                              logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode
        retCode = EVLAWritePlots (uv, 1, 0, plotFile, err, \
                                  plotDesc="Amplitude and phase calibration plots", \
                                  logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode
    # end SN table plot

    # Set up for CLCal - use phase & amp calibrators
    if not check:
        # Open and close image to sync with disk
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        clcal.solnVer = uv.GetHighVer("AIPS SN")
    else:
        clcal.solnVer = 1
    ical = 0
    if PCals:
        for PCal in PCals:
            clcal.calSour[ical] = PCal["Source"]
            ical += 1
    for ACal in ACals:
        if ACal["Source"] not in clcal.calSour:
            clcal.calSour[ical] = ACal["Source"]
            ical += 1
    # Apply to all
    mess = "Apply calibration for "+str(target)
    printMess(mess, logfile)
    mess = "Update CL "+str(clcal.calIn)+" with SN "+str(clcal.solnVer)+" to CL "+str(clcal.calOut)
    printMess(mess, logfile)

    if debug:
        clcal.i
        clcal.debug = debug
    # Trap failure
    try:
        if not check:
            clcal.g
    except Exception as exception:
        print(exception)
        mess = "clcal Failed retCode="+str(clcal.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLACal


def KATXPhase(inDELA, inUV, err, timeRange=[0.,0.], ChWid=0, doCalib=-1,
                gainUse=0, doBand=0, BPVer=0, flagVer=-1, BPSoln=0, CHWid=0,
                refAnt=0, solInt=0.0, logfile="", noScrat=[], check=False, debug=False):
    """ Perform Cross Phase calibration using auto-corrs on a delay calibrator scan and
        attach BP table to UV data

    Returns task error code, 0=OK, else failed
    inUV       = UV data to have BP table attached
    inDELA     = DELAY calibration UV data (Assumed just one required scan)
    err        = Obit error/message stack
    doCalib  = Apply calibration table, positive=>calibrate
    gainUse  = CL/SN table to apply
    doBand   = If >0.5 apply previous bandpass cal.
    ChWid    = use CWid channels in BP calibration
    Antennas = Antennas to use
    BPVer    = previous Bandpass table (BP) version
    flagVer  = Input Flagging table version
    timerange= timerange in days to use
    BPSoln    = output version of BP table
    refAnt   = Reference antenna number
    solInt   = Solution interval (min) BP table entries.
    taskLog  =Log file to write messages to INSTEAD of the terminal
    noScrat  =A list of AIPS disk numbers on which you do not 
             wish scratch files
    """
    ################################################################

    xphase = ObitTask.ObitTask("MKXPhase")
    try:
        xphase.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    OK = False   # Must have some work
    xphase.taskLog = logfile
    if not check:
        setname(inDELA, xphase)
        setoname(inUV, xphase)

    xphase.doBand    = doBand
    xphase.BPVer     = BPVer
    xphase.doCalib   = doCalib
    xphase.gainUse   = gainUse
    xphase.flagVer   = flagVer
    xphase.solInt    = solInt
    xphase.refAnt    = 0
    xphase.timeRange = timeRange
    xphase.ChWid     = ChWid
    xphase.BPSoln    = BPSoln
    xphase.taskLog   = logfile
    xphase.noScrat   = noScrat

    if debug:
            xphase.i
    xphase.debug = False
    # Trap failure
    try:
        if not check:
            xphase.g
    except Exception as exception:
        print(exception)
        mess = "MKXPhase Failed retCode="+str(xphase.retCode)
        printMess(mess, logfile)
        return 1
    else:
        OK = True

    return 0

def KATBPCal(uv, BPCals, err, newBPVer=1, timerange=[0.,0.], UVRange=[0.,0.], \
              doCalib=2, gainUse=0, doBand=0, BPVer=0, flagVer=-1,  \
              doCenter1=None, BChan1=1, EChan1=0, \
              BChan2=1, EChan2=0, ChWid2=1, Alpha=0.0, \
              solInt1=0.0, solInt2=0.0, solMode="A&P", refAnt=0, ampScalar=False, \
              doAuto=False, doPol=False, avgPol=False, avgIF=False, \
              doPlot=False, maxgap=30.0, plotFile="./BPCal.ps", \
              check=False, debug = False, nThreads=1, noScrat=[], logfile = ""):
    """
    Bandbass calibration

    Do bandbass calibration, write BP table
    Returns task error code, 0=OK, else failed
    Calibration is done in two passes

    1) First a wideband phase only calibration using channels
       BChan1 to EChan1 or the central doCenter1 fraction of the band
       using a solution interval of solInt1.  This solution is applied
       to all selected data and used in the second pass.
    2) Second channels in the range BChan2 to EChan2 averaging blocks
       of ChWid2 are calibrated using solType and solMode for solInt2 and
       the results written as the output BP table.

    The Calibrator model may be given as either and Image with CC table,
    a parameterized model or a point source with the flux density in
    the SU table.

    See BPass documentation for details

    * uv       = UV data object to calibrate
    * BPCals   = list of bandpass calibrators/models
    * err      = Obit error/message stack
    * newBPVer = output BP table
    * mergeBPVer= If >=0 (0= new highest Ver) then merge newBPVer and BPVer into mergeBPVer
    * doCalib  = Apply calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * doBand   = If >0.5 apply previous bandpass cal.
    * BPVer    = previous Bandpass table (BP) version
    * flagVer  = Input Flagging table version
    * timerange= timerange in days to use
    * doCenter1= If defined, the center fraction of the bandpass to use first pass
    * BChan1   = Low freq. channel,  initial cal
    * EChan1   = Highest freq channel, initial cal
    * BChan2   = Low freq. channel for BP cal
    * EChan2   = Highest freq channel for BP cal
    * ChWid2   = Number of channels in running mean BP soln,
    * solInt1  = first solution interval (min), 0=> scan average
    * solInt2  = second solution interval (min)
    * solMode  = solution mode 'A&P', 'P', 'P!A'
    * refAnt   = Reference antenna
    * ampScalar= If true, scalar average data in calibration
    * doAuto   = Use autocorrelation spectra? Else, crosscorrelation
    * doPol    = Apply polarization cal?
    * avgPol   = Avg. poln. in solutions?
    * avgIF    = Avg. IFs. in solutions?
    * doPlot   = If True make plots of corrected data
    * plotFile = Name of postscript file for plots
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * nThreads = Number of threads to use
    * noScrat  = list of AIPS disks to avoid for scratch files
    * logfile  = Log file for task
    """
    ################################################################
    mess =  "Bandpass calibrate data"
    printMess(mess, logfile)
    BPVer = uv.GetHighVer('AIPS BP') if BPVer == 0 else BPVer
    bpass = ObitTask.ObitTask("BPass")
    try:
        bpass.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    OK = False   # Must have some work
    bpass.taskLog = logfile
    if not check:
        setname(uv,bpass)
    bpass.doBand    = doBand
    bpass.BPVer     = BPVer
    bpass.doCalib   = doCalib
    bpass.gainUse   = gainUse
    bpass.flagVer   = flagVer
    bpass.doPol     = doPol
    bpass.solInt1   = solInt1
    bpass.solInt2   = solInt2
    bpass.solMode   = solMode
    bpass.refAnt    = refAnt
    bpass.timeRange = timerange
    bpass.UVRange   = UVRange
    bpass.ChWid2    = ChWid2
    bpass.doAuto    = doAuto
    bpass.avgPol    = avgPol
    bpass.avgIF     = avgIF
    bpass.ampScalar = ampScalar
    bpass.noScrat   = noScrat
    bpass.nThreads  = nThreads
    # Channel selection
    if not check:
        d     = uv.Desc.Dict
        nchan = d["inaxes"][d["jlocf"]]
    else:
        nchan = 1
    # Center fraction requested?
    if doCenter1:
        # Center doCenter1 fraction of channels for first cal
        mchan = int(nchan*doCenter1)
        bpass.BChan1 = max(1, (nchan/2)-(mchan/2))
        bpass.EChan1 = min(nchan, (nchan/2)+(mchan/2))
    else:
        bpass.BChan1 = BChan1
        bpass.EChan1 = EChan1
    bpass.BChan2 = BChan2
    bpass.EChan2 = EChan2
    if bpass.EChan2<=0:
        bpass.EChan2 = nchan

    # Loop over calibrators
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    hiBPVer = uv.GetHighVer('AIPS BP')
    if newBPVer <= 0:
        newBPVer = hiBPVer + 1
    outBPVer = newBPVer
    for BPCal in BPCals:
        thisOK = False
        bpass.Sources[0] = BPCal["Source"]
        bpass.BPSoln    = outBPVer
        bpass.Alpha     = BPCal["CalModelSI"]
        bpass.DataType2 = BPCal["CalDataType"]
        bpass.in2File   = BPCal["CalFile"]
        bpass.in2Name   = BPCal["CalName"]
        bpass.in2Class  = BPCal["CalClass"]
        bpass.in2Seq    = BPCal["CalSeq"]
        bpass.in2Disk   = BPCal["CalDisk"]
        bpass.nfield    = BPCal["CalNfield"]
        bpass.CCVer     = BPCal["CalCCVer"]
        bpass.BComp     = BPCal["CalBComp"]
        bpass.EComp     = BPCal["CalEComp"]
        bpass.Cmethod   = BPCal["CalCmethod"]
        bpass.Cmodel    = BPCal["CalCmodel"]
        bpass.Flux      = BPCal["CalFlux"]
        bpass.modelFlux = BPCal["CalModelFlux"]
        bpass.modelPos  = BPCal["CalModelPos"]
        if debug:
            bpass.i
        bpass.debug = False
        # Trap failure
        try:
            if not check:
                bpass.g
        except Exception as exception:
            print(exception)
            mess = "BPass Failed retCode="+str(bpass.retCode)
            printMess(mess, logfile)
            #return 1
        else:
            OK = True
            #Flush the table data to disk 
            uv.FullInstantiate(UV.READWRITE,err)
            # Do we have more than one Bandpass calibrator
            # Then we should merge the tables
            if outBPVer > newBPVer:
                origBP=UV.PGetTable(uv,UV.READWRITE,"AIPS BP",newBPVer,err)
                nextBP=UV.PGetTable(uv,UV.READWRITE,"AIPS BP",outBPVer,err)
                Table.PConcat(nextBP, origBP, err)
                uv.FullInstantiate(UV.READWRITE,err)
                uv.ZapTable("AIPS BP", outBPVer,err)
            else:
                outBPVer+=1
    # Something work?
    if not OK:
        printMess("All BPass calibration failed", logfile)
        return 1

    # Sort the final merged BP table
    uv.FullInstantiate(UV.READWRITE,err)
    origBP=UV.PGetTable(uv,UV.READWRITE,"AIPS BP",newBPVer,err)
    Table.PSort(origBP, "TIME", False, err)
    OErr.printErrMsg(err, "Error merging AIPS BP tables")

    # Merge input BP and output BP into mergeBPVer?
    if doBand>0.5:
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        mergeBPVer = uv.GetHighVer('AIPS BP') + 1
        mess =  "Merge BP %d and BP %d to BP %d" %(BPVer, newBPVer, mergeBPVer)
        printMess(mess, logfile)
        bpcal = ObitTask.ObitTask('BPCal')
        try:
            bpcal.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        bpcal.taskLog = logfile
        if not check:
            setname(uv,bpcal)
        bpcal.BPVer1 = BPVer
        bpcal.BPVer2 = newBPVer
        bpcal.BPOut  = mergeBPVer
        bpcal.doBand = doBand
        bpcal.refAnt = refAnt
        if debug:
            bpcal.i
        bpcal.debug = False
        # Trap failure
        try:
            if not check:
                bpcal.g
        except Exception as exception:
            print(exception)
            mess = "BPCal Failed retCode="+str(bpass.retCode)
            printMess(mess, logfile)
            return 1

    # Plot corrected data?
    if doPlot:
        scr = KATSpecPlot( uv, bpass.Sources, timerange, maxgap, refAnt, err, \
                            Stokes=["RR","LL"], doband=1,          \
                            plotFile=plotFile, check=check, logfile=logfile )
        if not UV.PIsA(scr):
            return 0   # tolerate failure
        retCode = EVLAWritePlots (scr, 1, 0, plotFile, err, \
                                  plotDesc="Bandpass calibration plots", \
                                  logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode
        scr.Zap(err)
        # end plots
    return 0
    # End EVLABPCal

def EVLASplit(uv, target, err, FQid=1, outClass="      ", logfile = "", \
                  check=False, debug = False):
    """
    Write calibrated data

    Returns task error code, 0=OK, else failed

    * uv       = UV data object to clear
    * target   = Target source name source name or list of names
    * err      = Obit error/message stack
    * FQid     = Frequency Id to process
    * logfile  = Log file for task
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    split=ObitTask.ObitTask("Split")
    try:
        split.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    split.taskLog = logfile
    if not check:
        setname(uv,split)
    if type(target)==list:
        split.Sources=target
    else:
        split.Sources=[target]
    split.doCalib = 2
    split.gainUse = 0
    split.flagVer = 1
    split.FreqID = FQid
    split.outClass = outClass
    split.outDisk  = split.inDisk
    if debug:
        split.i
        split.debug = debug
    # Trap failure
    try:
        if not check:
            split.g
    except Exception as exception:
        print(exception)
        mess = "split Failed retCode="+str(split.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    return 0
    # end EVLAsplit

def KATCalAvg(uv, avgClass, avgSeq, CalAvgTime,  err, \
               FQid=0, \
               flagVer=0, doCalib=2, gainUse=0, doBand=1, BPVer=0,  doPol=False, \
               BIF=1, EIF=0, BChan=1, EChan=0, doAuto=False, \
               avgFreq=0, chAvg=1, Compress=False, Stokes=' ', \
               nThreads=1, logfile = "", check=False, debug=False):
    """
    Calibrate, select and/or average data to a multisource file

    Returns task error code, 0=OK, else failed
    Generates NX and initial dummy CL table if needed

    * uv         = UV data object to clear
    * avgClass   = Class name of averaged data
    * avgSeq     = Sequence number of averaged data
    * CalAvgTime = Averaging time in sec
    * err        = Obit error/message stack
    * FQid       = Frequency Id to process, 0=>all
    * doCalib    = Apply calibration table, positive=>calibrate
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply previous bandpass cal.
    * BPVer      = previous Bandpass table (BP) version
    * doPol      = Calibrate polarization?
    * BIF        = first IF to copy
    * EIF        = highest IF to copy
    * BChan      = first channel to copy
    * EChan      = highest channel to copy
    * flagVer    = Input Flagging table version
    * avgFreq    = If 0 < avgFreq <= 1 then average channels
    * chAvg      = Number of channels to average
    * Compress   = Write "Compressed" data?
    * nThreads   = Number of threads to use
    * logfile    = Log file for task
    * check      = Only check script, don't execute tasks
    * debug      = Run tasks debug, show input
    """
    ################################################################
    mess =  "Average/calibrate data"
    printMess(mess, logfile)
    splat=ObitTask.ObitTask("Splat")
    try:
        splat.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    splat.taskLog = logfile
    if not check:
        setname(uv,splat)
    splat.doCalib  = doCalib
    splat.gainUse  = gainUse
    splat.doBand   = doBand
    splat.BPVer    = BPVer
    splat.doPol    = doPol
    splat.Stokes   = Stokes
    splat.BIF      = BIF
    splat.EIF      = EIF
    splat.BChan    = BChan
    splat.EChan    = EChan
    splat.flagVer  = flagVer
    splat.FreqID   = FQid
    splat.timeAvg  = CalAvgTime
    splat.avgFreq  = avgFreq
    splat.chAvg    = chAvg
    if doAuto:
        splat.corrType = 1   # include autocorrs
    else:
        splat.corrType = 0
    splat.Compress = Compress
    splat.outClass = avgClass
    splat.outDisk  = splat.inDisk
    splat.outSeq   = avgSeq
    splat.nThreads = nThreads
    if debug:
        splat.i
        splat.debug = debug
    # Trap failure
    try:
        if not check:
            splat.g
            pass
    except Exception as exception:
        print(exception)
        mess = "Splat Failed retCode="+str(splat.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    # end average

    # Get calibrated/averaged data, index and make CL table 1 if doCalib>0
    if not check:
        try:
            uvc = UV.newPAUV("AIPS UV DATA", splat.inName, avgClass, splat.inDisk, avgSeq, True, err)
            if err.isErr:
                print("Error creating cal/avg AIPS data")
                OErr.printErrMsg(err, "Error creating cal/avg AIPS data")
            # Dummy CL table
            solint = splat.timeAvg * 2   # CL table interval twice averaging
            # Open and close image to sync with disk
            uvc.Open(UV.READONLY, err)
            uvc.Close(err)
            hiver = uvc.GetHighVer("AIPS CL")
            if (doCalib>0) or (hiver<=0):
                UV.PTableCLGetDummy(uvc, uvc, 0, err, solInt=solint)
                pass
            if err.isErr:
                print("Error creating cal/avg AIPS data CL table")
                OErr.printErrMsg(err, "Error creating cal/avg AIPS data CL table")
            # Index - now in Splat
            #UV.PUtilIndex (uvc, err)
            if err.isErr:
                print("Error indexing cal/avg AIPS data")
                OErr.printErrMsg(err, "Error indexing cal/avg AIPS data")
            del uvc
        except Exception as exception:
            print(exception)
            OErr.printErr(err)
            mess = "Indexing or creating CL table failed"
            printMess(mess, logfile)
            return 1
        else:
            pass
    return 0
    # end EVLACalAvg

def KATBLCalAvg(uv, avgClass, avgSeq,  err, FQid=0, \
               flagVer=0, doCalib=2, gainUse=0, doBand=1, BPVer=0,  doPol=False, \
               BIF=1, EIF=0, BChan=1, EChan=0, maxFact=1.01, timeAvg=1.0, \
               avgFreq=0, chAvg=1, FOV=1.0, maxInt=1.0, Compress=False, Stokes=' ', \
               logfile = "", check=False, debug=False):
    """
    Calibrate, select and/or baseline dept. average data to a multisource file

    Returns task error code, 0=OK, else failed
    Generates NX and initial dummy CL table if needed

    * uv         = UV data object to clear
    * avgClass   = Class name of averaged data
    * avgSeq     = Sequence number of averaged data
    * CalAvgTime = Averaging time in sec
    * err        = Obit error/message stack
    * FQid       = Frequency Id to process, 0=>all
    * doCalib    = Apply calibration table, positive=>calibrate
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply previous bandpass cal.
    * BPVer      = previous Bandpass table (BP) version
    * doPol      = Calibrate polarization?
    * BIF        = first IF to copy
    * EIF        = highest IF to copy
    * BChan      = first channel to copy
    * EChan      = highest channel to copy
    * flagVer    = Input Flagging table version
    * avgFreq    = If 0 < avgFreq <= 1 then average channels
    * chAvg      = Number of channels to average
    * FOV        = Radius of field of view not to cause maxFact amp drop
    * maxInt     = Maximum integration time (min) for time averaging.
    * maxFact    = Maximum allowable additional amplitude loss.
    * Compress   = Write "Compressed" data?
    * logfile    = Log file for task
    * check      = Only check script, don't execute tasks
    * debug      = Run tasks debug, show input
    """
    ################################################################
    mess =  "Baseline dep Average/calibrate data"
    printMess(mess, logfile)
    uvavg=ObitTask.ObitTask("UVBlAvg")
    try:
        uvavg.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    uvavg.taskLog = logfile
    if not check:
        setname(uv,uvavg)
    uvavg.doCalib  = doCalib
    uvavg.gainUse  = gainUse
    uvavg.doBand   = doBand
    uvavg.BPVer    = BPVer
    uvavg.doPol    = doPol
    uvavg.Stokes   = Stokes
    uvavg.BIF      = BIF
    uvavg.EIF      = EIF
    uvavg.BChan    = BChan
    uvavg.EChan    = EChan
    uvavg.flagVer  = flagVer
    uvavg.FreqID   = FQid
    uvavg.avgFreq  = avgFreq
    uvavg.chAvg    = chAvg
    uvavg.FOV      = FOV
    uvavg.maxInt   = maxInt
    uvavg.maxFact  = maxFact
    uvavg.Compress = Compress
    uvavg.outClass = avgClass
    uvavg.outDisk  = uvavg.inDisk
    uvavg.outSeq   = avgSeq
    if debug:
        uvavg.i
        uvavg.debug = debug
    # Trap failure
    try:
        if not check:
            uvavg.g
            pass
    except Exception as exception:
        print(exception)
        mess = "UVBlAvg Failed retCode="+str(splat.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    # end average

    # Get calibrated/averaged data, index and make CL table 1 if doCalib>0
    if not check:
        try:
            uvc = UV.newPAUV("AIPS UV DATA", uvavg.inName, avgClass, uvavg.inDisk, avgSeq, True, err)
            if err.isErr:
                print("Error creating cal/avg AIPS data")
                OErr.printErrMsg(err, "Error creating cal/avg AIPS data")
            # Dummy CL table
            solint = timeAvg * 2   # CL table interval twice averaging
            # Open and close image to sync with disk
            uvc.Open(UV.READONLY, err)
            uvc.Close(err)
            hiver = uvc.GetHighVer("AIPS CL")
            if (doCalib>0) or (hiver<=0):
                UV.PTableCLGetDummy(uvc, uvc, 0, err, solInt=solint)
                pass
            if err.isErr:
                print("Error creating cal/avg AIPS data CL table")
                OErr.printErrMsg(err, "Error creating cal/avg AIPS data CL table")
            if err.isErr:
                print("Error indexing cal/avg AIPS data")
                OErr.printErrMsg(err, "Error indexing cal/avg AIPS data")
            del uvc
        except Exception as exception:
            print(exception)
            OErr.printErr(err)
            mess = "Indexing or creating CL table failed"
            printMess(mess, logfile)
            return 1
        else:
            pass
    return 0
    # end EVLACalAvg

def EVLACalAvg2(uv, avgClass, avgSeq, CalAvgTime,  err,  FQid=0, \
                flagVer=0, doCalib=2, gainUse=0, doBand=1, BPVer=0, doPol=False,  \
                BIF=1, EIF=0, BChan=1, EChan=0, chAvg=1, Compress=False, \
                logfile = "", check=False, debug=False):
    """
    Calibrate and average data to a multisource file

    Returns task error code, 0=OK, else failed
    Generates NX and initial dummy CL table

    * uv         = UV data object to clear
    * avgClass   = Class name of averaged data
    * avgSeq     = Sequence number of averaged data
    * CalAvgTime = Averaging time in sec
    * err        = Obit error/message stack
    * FQid       = Frequency Id to process, 0=>all
    * doPol      = Calibrate polarization?
    * doCalib    = Apply calibration table, positive=>calibrate
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply previous bandpass cal.
    * BPVer      = previous Bandpass table (BP) version
    * BIF        = first IF to copy
    * EIF        = highest IF to copy
    * BChan      = first channel to copy
    * EChan      = highest channel to copy
    * flagVer    = Input Flagging table version
    * Compress   = Write "Compressed" data?
    * logfile    = Log file for task
    * check      = Only check script, don't execute tasks
    * debug      = Run tasks debug, show input
    """
    ################################################################
    mess =  "Average/calibrate calibrate data"
    printMess(mess, logfile)
    outuv = None
    # Create output
    if not check:
        # Set calibration, editing and selection
        info = uv.List
        info.set("doCalSelect",  True)
        info.set("FreqID",  FQid)
        info.set("doPol",   doPol)
        info.set("doCalib", doCalib)
        info.set("gainUse", gainUse)
        info.set("doBand",  doBand)
        info.set("doPol",   doPol)
        info.set("BPVer",   BPVer)
        info.set("BIF",     BIF)
        info.set("EIF",     EIF)
        info.set("BChan",   BChan)
        info.set("EChan",   EChan)
        info.set("flagVer", flagVer)
        info.set("Compress", Compress,)
        #print "info", info.Dict  # DEBUG
        # Open and close to set
        uv.Open(UV.READCAL, err)
        outuv = UV.newPAUV("CalAvg", uv.Aname, avgClass, uv.Disk, avgSeq, False, err)
        uv.Clone (outuv, err)
        uv.Close(err)
        #outuv.Header(err) # debug
        if err.isErr:
            print("Error creating cal/avg AIPS uv data")
            OErr.printErrMsg(err, "Error creating cal/avg AIPS data")

    # Average
    if not check:
        try:
            mess = "Copy/average/calibrate data to "+\
                   outuv.Aname+" . "+outuv.Aclass+" . "+str(outuv.Disk)+ \
                   " . "+str(outuv.Aseq)+" cno: "+str(outuv.Acno)
            printMess(mess, logfile)
            info = outuv.List
            info.set("Compress", Compress,)
            UV.PUtilAvgT (uv, outuv, err, timeAvg=CalAvgTime/60.)
            if err.isErr:
                print("Error cal/avg AIPS uv data")
                OErr.printErrMsg(err, "Error cal/avg AIPS data")


            # Do History - previous already copied
            if outuv:
                del outuv
            outuv = UV.newPAUV("CalAvg", uv.Aname, avgClass, uv.Disk, avgSeq, True, err)
            #print "DEBUG Copy history"
            outHistory = History.History("outhistory", outuv.List, err)

            # Add history
            #print "DEBUG Add history"
            outHistory.Open(History.READWRITE, err)
            outHistory.TimeStamp(" Start Obit CalAvg",err)
            outHistory.WriteRec(-1,"CalAvg  CalAvgTime = "+str(CalAvgTime),err)
            outHistory.WriteRec(-1,"CalAvg  inName = "+uv.Aname,  err)
            outHistory.WriteRec(-1,"CalAvg  inClass = "+uv.Aclass, err)
            outHistory.WriteRec(-1,"CalAvg  inDisk = " +str(uv.Disk),err)
            outHistory.WriteRec(-1,"CalAvg  inSeq = " +str(uv.Aseq),err)
            outHistory.WriteRec(-1,"CalAvg  FreqID = "+str(FQid),err)
            outHistory.WriteRec(-1,"CalAvg  doPol = "+str(doPol),err)
            outHistory.WriteRec(-1,"CalAvg  doCalib = "+str(doCalib),err)
            outHistory.WriteRec(-1,"CalAvg  gainUse = "+str(gainUse),err)
            outHistory.WriteRec(-1,"CalAvg  doBand = "+str(doBand),err)
            outHistory.WriteRec(-1,"CalAvg  BPVer = "+str(BPVer),err)
            outHistory.WriteRec(-1,"CalAvg  BIF = "+str(BIF),err)
            outHistory.WriteRec(-1,"CalAvg  EIF = "+str(EIF),err)
            outHistory.WriteRec(-1,"CalAvg  BChan = "+str(BChan),err)
            outHistory.WriteRec(-1,"CalAvg  EChan = "+str(EChan),err)
            outHistory.WriteRec(-1,"CalAvg  flagVer = "+str(flagVer),err)
            outHistory.WriteRec(-1,"CalAvg  Compress = "+str(Compress),err)
            outHistory.Close(err)
            #print "DEBUG Copy history done"
            if err.isErr:
                print("Error cal/avg History")
                OErr.printErrMsg(err, "Error cal/avg History")
                # end copy+history
        except Exception as exception:
            print(exception)
            OErr.printErr(err)
            mess = "Calibrate and average uv data failed"
            printMess(mess, logfile)
            return 1
        else:
            pass

    # Index and make CL table
    if not check:
        try:
            # Dummy CL table
            solint = 2 * CalAvgTime/60.   # CL table interval twice averaging
            UV.PTableCLGetDummy(outuv, outuv, 0, err, solInt=solint)
            if err.isErr:
                print("Error creating cal/avg AIPS data CL table")
                OErr.printErrMsg(err, "Error creating cal/avg AIPS data CL table")
            # Index
            UV.PUtilIndex (outuv, err)
            if err.isErr:
                print("Error indexing cal/avg AIPS data")
                OErr.printErrMsg(err, "Error indexing cal/avg AIPS data")
        except Exception as exception:
            print(exception)
            OErr.printErr(err)
            mess = "Indexing or creating CL table failed"
            printMess(mess, logfile)
            return 1
        else:
            pass
    if outuv:
        del outuv
    return 0
    # end EVLACalAvg2

def EVLASetImager (uv, target, outIclass="", nThreads=1, noScrat=[], logfile = "", check=False):
    """
    Setup to run Imager or MFImage

    return MFImage task interface object

    * uv       = UV data object to image
    * target   = Target source name or list of names
    * outIclass= output class
    * FQid     = Frequency Id to process
    * nThreads = Number of threads to use
    * noScrat  = list of disks to avoid for scratch files
    * logfile  = Log file for task
    """
    ################################################################
    img = ObitTask.ObitTask("MFImage")
    try:
        img.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as e:
        print(e)
        pass
    img.taskLog = logfile
    if not check:
        setname(uv,img)
    img.outDisk  = img.inDisk
    img.out2Disk = img.inDisk
    if type(target)==list:
        img.Sources=target
    else:
        img.Sources=[target]
    img.outClass   = outIclass
    img.doCalib    = 2
    img.doBand     = 1
    img.UVTaper    = [0.0, 0.0, 0.0]
    img.UVRange    = [0.0,0.0]
    img.FOV        = 0.05
    img.autoWindow = True
    img.BLFact     = 1.01
    img.BLchAvg    = True
    img.Niter      = 5000
    img.Gain       = 0.10
    img.maxPSCLoop = 3
    img.minFluxPSC= 0.5
    img.solPInt   = 10.0/60.
    img.solPType  = "L1"
    img.maxASCLoop= 1
    img.minFluxPSC= 1.5
    img.solAInt   = 1.0
    img.minSNR    = 3.0
    img.avgPol    = True
    img.avgIF     = True
    img.nThreads  = nThreads
    img.noScrat   = noScrat
    return img
# end EVLASetImager

def EVLARLDelay(uv, err, \
                RLDCal=None, BChan=1, EChan = 0,\
                UVRange=[0.0,0.0], timerange = [0.0,1000.0], \
                soucode="    ", doCalib=-1, gainUse=0, \
                doBand=0, BPVer=0, flagVer=-1,  \
                refAnt=0, Antennas=[0], doPol=-1,  \
                nThreads=1, noScrat=[], logfile = "",check=False, debug = False):
    """
    Determine R-L delay

    Returns task error code, 0=OK, else failed
    R-L Delay calibration creating and applying new AIPS SN table
    to (new) highest numbered CL table on uv

    * uv       = UV data object to clear
    * err      = Obit error/message stack
    * RLDCal   = An array of triplets with R-L calibrators:
      (name, R-L phase (deg at 1 GHz), RM (rad/m**2))
      NB: more than 1 may be a bad idea
    * BChan    = First (1-rel) channel number
    * EChan    = Highest channel number. 0=> high in data.
    * UVRange  = Range of baseline used in kilowavelengths
    * soucode  = Calibrator code
    * doCalib  = Apply calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * timerange= time range of data (days)
    * doBand   = If >0.5 apply previous bandpass cal.
    * BPVer    = previous Bandpass table (BP) version
    * flagVer  = Flagging table to apply
    * refAnt   = Reference antenna REQUIRED
    * Antennas = List of antennas to include
    * doPol    = Apply polarization cal?
    * noScrat  = list of AIPS disks to avoid for scratch files
    * nThreads = Number of threads to use in imaging
    * logfile  = Log file for task
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    # Don't bother if not full polarization
    d     = uv.Desc.Dict
    nstoke = d["inaxes"][d["jlocs"]]
    if nstoke<4:
        mess = "Skip XPol delay corrections - not full stokes"
        printMess(mess, logfile)
        return 0
    mess =  "XPol delay calibration "
    printMess(mess, logfile)

    ncal = len(RLDCal)  # How many calibrators?
    OK = False   # Must have some work
    rldly=ObitTask.ObitTask("RLDly")
    try:
        rldly.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    rldly.taskLog = logfile
    if not check:
        setname(uv,rldly)
        rldly.Antennas = Antennas
    rldly.timeRange[0] = timerange[0]
    rldly.timeRange[1] = timerange[1]
    rldly.BChan   = BChan
    rldly.EChan   = EChan
    rldly.UVR_Full[0] = UVRange[0];
    rldly.UVR_Full[1] = UVRange[1];
    rldly.doCalib = doCalib
    rldly.gainUse = gainUse
    rldly.flagVer = flagVer
    rldly.doPol   = doPol
    rldly.doBand  = doBand
    rldly.BPVer   = BPVer
    rldly.refAnt  = refAnt
    rldly.minSNR  = 1  # Minimum SNR - this should be passed
    rldly.prtLv   = 1
    rldly.nThreads = nThreads
    # Loop over calibrators
    for ical in range (0,ncal):
        rldly.Sources[0]= RLDCal[ical][0]
        rldly.RLPhase   = RLDCal[ical][1]
        rldly.RM        = RLDCal[ical][2]
        mess =  "R-L delay calibration using "+rldly.Sources[0]
        printMess(mess, logfile)
        if debug:
            print("timerange", rldly.timerang)
            rldly.i
            rldly.debug = True
        # Trap failure
        try:
            if not check:
                rldly.g
        except Exception as exception:
            print(exception)
            mess = "rldly Failed retCode="+str(rldly.retCode)
            printMess(mess, logfile)
            #return 1
        else:
            OK = True
        # end loop over calibrators

    # Something work?
    if not OK:
        printMess("All RLDelay calibration failed", logfile)
        return 1

    # Get output SN table
    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    lsnver = uv.GetHighVer("AIPS SN")

    # Apply to CL table
    retCode = EVLAApplyCal(uv, err, SNver=lsnver, CLin = gainUse, \
                           maxInter=1440.0, \
                           logfile=logfile, check=check,debug=debug)
    if retCode!=0:
        return retCode

    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    # end R-L delay cal

    return 0
    # end EVLARLDelay

def EVLAPolCal(uv, InsCals, err, RM=0.0, \
               doCalib=2, gainUse=0, doBand=1, BPVer=0, flagVer=-1, \
               solType="    ", fixPoln=False, avgIF=False, \
               solInt=0.0, refAnt=0, ChInc=1, ChWid=1, \
               pmodel=[0.0,0.0,0.0,0.0,0.0,0.0,0.0], \
               check=False, debug = False, \
               nThreads=1, noScrat=[], logfile = ""):
    """
    Instrumental Polarization

    Do Instrumental
    Instrumental cal uses PCal
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to calibrate
    * InsCals  = Instrumental poln calibrators, name or list of names
      If None no instrumental cal
    * err      = Obit error/message stack
    * RM       = NYI Rotation measure of RLCal
    * doCalib  = Apply prior calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * doBand   = >0 => apply bandpass calibration
    * BPVer    = AIPS BP table to apply
    * flagVer  = Input Flagging table version
    * solType  = solution type, "    ", "LM  "
    * fixPoln  = NYI if True, don't solve for source polarization in ins. cal
    * avgIF    = NYI if True, average IFs in ins. cal.
    * solInt   = instrumental solution interval (min)
    * refAnt   = Reference antenna
    * ChInc    = channel increment for solutions
    * ChWid    = number of channels to average for solution.
    * pmodel   = NYI Instrumental poln cal source poln model.

      =========  ========================
      pmodel[0]  I flux density (Jy)
      pmodel[1]  Q flux density (Jy)
      pmodel[2]  U flux density (Jy)
      pmodel[3]  V flux density (Jy)
      pmodel[4]  X offset in sky (arcsec)
      pmodel[5]  Y offset in sky (arcsec)
      =========  ========================

    * nThreads = Number of threads to use in imaging
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * noScrat  = list of disks to avoid for scratch files
    * logfile  = Log file for task
    """
    ################################################################
    # Don't bother if not full polarization
    d     = uv.Desc.Dict
    nstoke = d["inaxes"][d["jlocs"]]
    if nstoke<4:
        mess = "Skip Instrumental polarization corrections - not full stokes"
        printMess(mess, logfile)
        return 0
    mess =  "Instrumental polarization calibration "
    printMess(mess, logfile)
    # Instrumental calibration
    if InsCals!=None:
        pcal = ObitTask.ObitTask("PCal")
        try:
            pcal.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        pcal.logFile = logfile
        if not check:
            setname(uv,pcal)
        if type(InsCals)==list:
            pcal.Sources = InsCals
        else:
            pcal.Sources = [InsCals]
        pcal.doCalib  = doCalib
        pcal.gainUse  = gainUse
        pcal.doBand   = doBand
        pcal.BPVer    = BPVer
        pcal.flagVer  = flagVer
        pcal.solnType = solType
        pcal.solInt   = solInt
        pcal.ChInc    = ChInc
        pcal.ChWid    = ChWid
        pcal.refAnt   = refAnt
        pcal.prtLv    = 2
        pcal.PDSoln   = 1
        pcal.CPSoln   = 1
        pcal.nThreads = nThreads
        for i in range(0,len(pcal.doFitI)):
            pcal.doFitI[i]   = True
        pcal.taskLog  = logfile
        i = 1;
        for d in noScrat:
            pcal.noScrat[i] = d
            i += 1
        if debug:
            pcal.i
            pcal.debug = debug
        # Trap failure
        try:
            if not check:
                pcal.g
        except Exception as exception:
            print(exception)
            mess = "PCal Failed retCode="+str(pcal.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
    # end instrumental poln cal

    return 0
    # End EVLAPolCal

def EVLARLCal(uv, err, \
              RLDCal=None, BChan=1, EChan = 0, ChWid2=1, solInt1=1./6, solInt2=10., \
              RLPCal=None, RLPhase=0.0, RM=0.0, UVRange=[0.0,0.0], timerange = [0.0,1000.0], \
              FQid=0, calcode="    ", doCalib=-1, gainUse=0, \
              doBand=0, BPVer=0, flagVer=-1,  \
              refAnt=0, doPol=-1, PDVer=1, FOV=0.05, niter = 100, CleanRad=None, \
              doPlot=False, maxgap=30.0, plotFile="./BPCal.ps", \
              nThreads=1, noScrat=[], logfile = "",check=False, debug = False):
    """
    Determine R-L delay and/or phase calibration

    Returns task error code, 0=OK, else failed
    R-L Delay calibration using new BP table, if R-L phase (& RM) known for
    calibrator(s), this also does the R-L phase calibration
    R-L Phase Calibration applies to (new) highest numbered CL table on uv

    * uv       = UV data object to clear
    * err      = Obit error/message stack
    * RLPCal   = R-L (polarization angle) calibrator,
      If None no R-L cal
    * RLPhase  = R-L phase of RLPCal (deg) at 1 GHz
    * RM       = R-L phase RM (NYI)
    * RLDCal   = An array of triplets with R-L calibrators:
      (name, R-L phase (deg at 1 GHz), RM (rad/m**2))
      If None no R-L delay cal
    * solInt1  = first solution interval (min), 0=> scan average
    * solInt2  = second solution interval (min)
    * RLDPhase = R-L phase of RLPCal (deg) at 1 GHz
    * BChan    = First (1-rel) channel number
    * EChan    = Highest channel number. 0=> high in data.
    * ChWid2   = Number of channels in running mean RL BP soln,
    * UVRange  = Range of baseline used in kilowavelengths
    * FQid     = Frequency Id to process
    * calcode  = Calibrator code
    * doCalib  = Apply calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * timerange= time range of data (days)
    * doBand   = If >0.5 apply previous bandpass cal.
    * BPVer    = previous Bandpass table (BP) version
    * flagVer  = Flagging table to apply
    * refAnt   = Reference antenna REQUIRED
    * doPol    = Apply polarization cal?
    * PDVer    = PD version for pol cal, -1=>use IF
    * FOV      = field of view radius (deg) needed to image RLPCal
    * niter    = Number  of iterations of CLEAN in R-L cal
    * CleanRad = CLEAN radius about center or None=autoWin
    * doPlot   = If True make plots of corrected data
    * plotFile = Name of postscript file for plots
    * noScrat  = list of AIPS disks to avoid for scratch files
    * nThreads = Number of threads to use in imaging
    * logfile  = Log file for task
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    # Don't bother if not full polarization
    d     = uv.Desc.Dict
    nstoke = d["inaxes"][d["jlocs"]]
    if nstoke<4:
        mess = "Skip R-L polarization corrections - not full stokes"
        printMess(mess, logfile)
        return 0
    mess =  "R-L polarization calibration "
    printMess(mess, logfile)

    lbpver = BPVer  # default bandpass in imaging
    # Want R-L phase cal using delay calibrators?
    if RLDCal!=None:
        ncal = len(RLDCal)  # How many calibrators?
        rlpass=ObitTask.ObitTask("RLPass")
        try:
            rlpass.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        rlpass.taskLog = logfile
        if not check:
            setname(uv,rlpass)
            #if Antennas:
            #    i = 0
            #    for a in Antennas:
            #        rlpass.Antennas[i] = a; i  += 1
            rlpass.timeRange[0] = timerange[0]
            rlpass.timeRange[1] = timerange[1]
            rlpass.BChan1  = BChan
            rlpass.EChan1  = EChan
            rlpass.BChan2  = BChan
            rlpass.EChan2  = EChan
            rlpass.ChWid2  = ChWid2
            rlpass.UVRange[0] = UVRange[0];
            rlpass.UVRange[1] = UVRange[1];
            rlpass.doCalib = doCalib
            rlpass.gainUse = gainUse
            rlpass.flagVer = flagVer
            rlpass.FreqID  = FQid
            rlpass.doPol   = doPol
            if "PDVer" in rlpass.__dict__:
                rlpass.PDVer = PDVer
            rlpass.doBand  = doBand
            rlpass.BPVer   = BPVer
            rlpass.refAnt  = refAnt
            rlpass.solInt1 = solInt1
            rlpass.solInt2 = solInt2
            rlpass.BPSoln  = 0
            rlpass.prtLv   = 1
            rlpass.nThreads = nThreads
            # Loop over calibrators
            for ical in range (0,ncal):
                rlpass.Sources[0]= RLDCal[ical][0]
                rlpass.RLPhase   = RLDCal[ical][1]
                rlpass.RM        = RLDCal[ical][2]
                mess =  "R-L channel phase calibration using "+rlpass.Sources[0]
                printMess(mess, logfile)
                if debug:
                    print("timerange", rlpass.timerang)
                    rlpass.i
                    rlpass.debug = True
                # Trap failure
                try:
                    if not check:
                        rlpass.g
                except Exception as exception:
                    print(exception)
                    mess = "rlpass Failed retCode="+str(rlpass.retCode)
                    printMess(mess, logfile)
                    return 1
                else:
                    pass
            # end loop over calibrators
        # Get output BP table
        # Open and close image to sync with disk
        uv.Open(UV.READONLY, err)
        uv.Close(err)
        lbpver = uv.GetHighVer("AIPS BP")
    # end R-L delay cal

    # R-L phase cal
    if RLPCal!=None:
        mess =  "R-L IF phase calibration using "+RLPCal
        printMess(mess, logfile)
        img = ObitTask.ObitTask("Imager")
        try:
            img.userno     = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        img.taskLog    = logfile
        if not check:
            setname(uv,img)
        if RLDCal==None:
            img.doBand = doBand
            img.BPVer  = lbpver
        else:
            img.doBand = 1
            img.BPVer  = lbpver  # Just created one
        img.doCalib    = doCalib
        img.gainUse    = gainUse
        img.flagVer    = flagVer
        img.doPol      = True
        img.Sources[0] = RLPCal
        img.Stokes     = "IQU"
        img.FOV        = FOV
        img.Niter      = niter
        # Auto window or centered box
        if CleanRad:
            img.CLEANBox=[-1,CleanRad,0,0]
        else:
            img.autoWindow  = True
        img.dispURL    = "None"
        img.BLFact     = 1.004
        img.Catalog    = "None"
        img.nThreads   = nThreads
        img.maxPSCLoop = 2
        img.minFluxPSC = 0.05
        img.solPInt    = solInt1
        img.solPType   = "L1"
        img.prtLv      = 2
        img.noScrat    = noScrat
        # Temporary output files
        if img.DataType=="AIPS":
            img.outName = "TEMP"
            img.outClass= "IPOLCL"
            img.outDisk = img.inDisk
            img.outSeq  = 6666
            img.out2Name = "TEMP"
            img.out2Class= "IPOLCL"
            img.out2Disk = img.inDisk
            img.out2Seq  = 7777
        elif img.DataType=="FITS":
            img.outFile  = "TEMPPOLCAL.fits"
            img.outDisk  = img.inDisk
            img.out2File = "TEMPPOLCAL2.uvtab"
            img.out2Disk = img.inDisk

        # How many IFs?
        if not check:
            h = uv.Desc.Dict
            if h["jlocif"]>=0:
                nif = h["inaxes"][h["jlocif"]]
            else:
                nif = 1
        else:
            nif = 1

        # Lists of flux densities and RMSes
        IFlux = []
        IRMS  = []
        QFlux = []
        QRMS  = []
        UFlux = []
        URMS  = []

        # Loop over IF imaging I,Q, U, allow failure
        for iif in range (1, nif+1):
            img.BIF = iif
            img.EIF = iif
            #img.dispURL    = "ObitView"  # DEBUG
            #img.debug=True               # DEBUG
            if debug:
                img.i
                img.debug = debug
            # Trap failure
            failed = False
            try:
                if not check:
                    img.g
            except Exception as exception:
                print(exception)
                mess = "Imager Failed IF "+str(iif)+" retCode="+str(img.retCode)
                printMess(mess, logfile)
                failed = True
            else:
                pass
            # Stub if failed
            if failed:
                IFlux.append(-1.0)
                IRMS.append(-1.0)
                QFlux.append(-1.0)
                QRMS.append(-1.0)
                UFlux.append(-1.0)
                URMS.append(-1.0)
                continue

            if check:      # Don't bother if only checking
                continue
            # Get fluxes from inner quarter of images
            if img.DataType=="AIPS":
                outName = (img.Sources[0].strip()+"TEMP")[0:12]
                outDisk = img.outDisk
                outSeq  = 6666
                # Stokes I
                outClass="IPOLCL"
                # Test if image exists
                user =  OSystem.PGetAIPSuser();
                cno = AIPSDir.PTestCNO(outDisk, user, outName[0:12], outClass[0:6], "MA", outSeq, err)
                if cno >= 0 :
                    x =  Image.newPAImage("I",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    h = x.Desc.Dict
                    blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                    trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                    try:
                        stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                        IFlux.append(stat["Flux"])
                        IRMS.append(stat["RMSHist"])
                        x.Zap(err)  # Cleanup
                        del x
                    except:
                        IFlux.append(-1.0)
                        IRMS.append(-1.0)
                else:
                    IFlux.append(-1.0)
                    IRMS.append(-1.0)
                # Stokes Q
                outClass="QPOLCL"
                cno = AIPSDir.PTestCNO(outDisk, user, outName[0:12], outClass[0:6], "MA", outSeq, err)
                if cno > 0 :
                    x =  Image.newPAImage("Q",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    h = x.Desc.Dict
                    blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                    trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                    try:
                        stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                        QFlux.append(stat["Flux"])
                        QRMS.append(stat["RMSHist"])
                        x.Zap(err)  # Cleanup
                        del x
                    except:
                        QFlux.append(-1.0)
                        QRMS.append(-1.0)
                else:
                    QFlux.append(-1.0)
                    QRMS.append(-1.0)
                # Stokes U
                outClass="UPOLCL"
                cno = AIPSDir.PTestCNO(outDisk, user, outName[0:12], outClass[0:6], "MA", outSeq, err)
                if cno > 0 :
                    x =  Image.newPAImage("U",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    h = x.Desc.Dict
                    blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                    trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                    try:
                        stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                        UFlux.append(stat["Flux"])
                        URMS.append(stat["RMSHist"])
                        x.Zap(err)  # Cleanup
                        del x
                    except:
                        UFlux.append(-1.0)
                        URMS.append(-1.0)
                else:
                    UFlux.append(-1.0)
                    URMS.append(-1.0)
                # Delete UV output
                out2Name = (img.Sources[0].strip()+"TEMP")[0:12]
                out2Class="IPOLCL"
                out2Disk = img.inDisk
                out2Seq  = 7777
                u =  UV.newPAUV("UV",out2Name,out2Class,out2Disk,out2Seq,True,err)
                u.Zap(err)
                del u
            elif img.DataType=="FITS":
                # Stokes I
                outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                x =  Image.newPFImage("I",outFile,img.outDisk,True,err)
                h = x.Desc.Dict
                blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                IFlux.append(stat["Flux"])
                IRMS.append(stat["RMSHist"])
                x.Zap(err)  # Cleanup
                del x
                # Stokes Q
                outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                x =  Image.newPFImage("Q",outFile,img.outDisk,True,err)
                stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                IFlux.append(stat["Flux"])
                IRMS.append(stat["RMSHist"])
                x.Zap(err)  # Cleanup
                del x
                # Stokes U
                outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                x =  Image.newPFImage("Q",outFile,img.outDisk,True,err)
                stat = imstat(x, err, blc=blc,trc=trc,logfile=None)
                IFlux.append(stat["Flux"])
                IRMS.append(stat["RMSHist"])
                x.Zap(err)  # Cleanup
                del x
                # out2File = img.Sources[0].strip()+"TEMPPOLCAL2.uvtab"
                u =  UV.newPFUV("UV",outFile,img.outDisk,True,err)
                u.Zap(err)
                del u
           # End accumulate statistics by file type
        # End loop over IF

        # Give results, compute R-L correction
        RLCor = []
        import math
        mess = " IF     IFlux    IRMS    QFlux   QRMS    UFlux  URMS  R-L Corr"
        printMess(mess, logfile)
        for i in range (0,len(IFlux)):
            # REALLY NEED RM Correction!!!!!
            cor = RLPhase - 57.296 * math.atan2(UFlux[i],QFlux[i])
            RLCor.append(cor)
            mess = "%3d  %8.3f %8.4f %7.3f %7.4f %7.3f %7.4f %7.2f "%\
                (i+1, IFlux[i], IRMS[i], QFlux[i], QRMS[i], UFlux[i], URMS[i], cor)
            printMess(mess, logfile)
        # Copy gainUse to new highest CL table
        if not check:
            # Open and close image to sync with disk
            uv.Open(UV.READONLY, err)
            uv.Close(err)
            hiCL = uv.GetHighVer("AIPS CL")
        else:
            hiCL = 1

        # Copy CL table to be modified
        if not check:
            EVLACopyTable (uv, uv, "AIPS CL", err, inVer=hiCL, outVer=hiCL+1, \
                           logfile=logfile, check=check, debug=debug)
        if err.isErr:
            print("Error copying CL Table")
            return 1

        # Apply R-L phase corrections
        clcor = AIPSTask.AIPSTask("clcor")
        try:
            clcor.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        clcor.logFile  = logfile
        if not check:
            setname(uv,clcor)
        clcor.opcode   = "POLR"
        clcor.gainver  = hiCL+1
        clcor.gainuse  = hiCL+1
        clcor.clcorprm[1:] = RLCor
        if debug:
            clcor.i
            clcor.debug = debug
        # Trap failure
        try:
            if not check:
                clcor.g
        except Exception as exception:
            print(exception)
            mess = "CLCOR Failed retCode="+str(clcor.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
        # end R-L Cal
    # Plot corrected data?
    if doPlot:
        if RLPCal:
            pSou = RLPCal
        else:
            pSou = RLDCal[0][0]
        atimerange = []
        for i in range(0,8):
            atimerange.append(0.0)
        atimerange[0] = timerange[0]; atimerange[4] = timerange[1];
        scr = KATSpecPlot( uv, pSou, atimerange, maxgap, refAnt, err,    \
                                Stokes=["RL","LR"], doband=1, doPol=doPol, PDVer=PDVer,  \
                                plotFile=plotFile, \
                                check=check, debug=debug, logfile=logfile )
        if not scr.UVIsA():
            return 0   # tolerate failure
        retCode = EVLAWritePlots (scr, 1, 0, plotFile, err, \
                                  plotDesc="R-L phase/delay plots", \
                                  logfile=logfile, check=check, debug=debug)
        if retCode!=0:
            return retCode
        scr.Zap(err)
        # end plots
    return 0
    # end EVLARLCal

def EVLARLCal2(uv, err, uv2 = None, \
               RLDCal=None, BChan=1, EChan = 0,  \
               FQid=0, calcode="    ", doCalib=-1, gainUse=0, \
               timerange = [0.,0.,0.,0.,0.,0.,0.,0.], \
               doBand=0, BPVer=0, flagVer=-1, \
               refAnt=0, doPol=-1, smooth=[0.,0.,0.], dataInt=0., \
               RLPCal=None,  FOV=0.05, niter = 100, \
               nThreads=1, noScrat=[], logfile = "",check=False, debug = False):
    """
    Determine R-L delay and phase calibration

    Returns task error code, 0=OK, else failed
    Calibration applies to (new) highest numbered CL table on uv

    * uv       = UV data object to clear
    * err      = Obit error/message stack
    * uv2      = If gives, then copy AN table from uv to uv2 and apply same
      calibration (intended to calibrate CVel data)
    * RLPCal   = An array of triplets with R-L calibrators:
      (name, R-L phase (deg at 1 GHz), RM (rad/m**2))
      If None no R-L cal
    * RLDCal   = R-L delay calibrator name or list
      If None no R-L delay cal
    * BChan    = First (1-rel) channel number
    * EChan    = Highest channel number. 0=> high in data.
    * FQid     = Frequency Id to process
    * calcode  = Calibrator code
    * doCalib  = Apply calibration table, positive=>calibrate
    * gainUse  = CL/SN table to apply
    * timerange= time range of data (aips format)
    * doBand   = If >0.5 apply previous bandpass cal.
    * BPVer    = previous Bandpass table (BP) version
    * flagVer  = Flagging table to apply
    * refAnt   = Reference antenna REQUIRED
    * doPol    = Apply polarization cal?
    * smooth   = Channel smoothing function
    * dataInt  = Data integration time (sec)
    * FOV      = field of view radius (deg) needed to image RLPCal
    * niter    = Number  of iterations of CLEAN in R-L cal
    * noScrat  = list of AIPS disks to avoid for scratch files
    * nThreads = Number of threads to use in imaging
    * logfile  = Log file for task
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    """
    ################################################################
    mess =  "R-L polarization calibration "
    printMess(mess, logfile)
    # Want R-L delay cal?
    if RLDCal!=None:
        rldly=ObitTask.ObitTask("rldly")
        try:
            rldly.userno  = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        rldly.logFile = logfile
        if not check:
            setname(uv,rldly)
        if type(RLDCal)!=list:
            rldly.calsour[1]=RLDCal
        else:
            i = 1
            for t in RLDCal:
                rldly.calsour[i] = t
                i  += 1
        i = 1
        for t in timerange:
            rldly.timerang[i] = t
            i  += 1
        rldly.bchan   = BChan
        rldly.echan   = EChan
        rldly.docalib = doCalib
        rldly.gainuse = gainUse
        rldly.flagver = flagVer
        rldly.freqid  = FQid
        rldly.calcode = calcode
        rldly.dopol   = doPol
        rldly.smooth[1]=smooth[0]; rldly.smooth[2]=smooth[1];rldly.smooth[3]=smooth[2];
        rldly.doband  = doBand
        rldly.bpver   = BPVer
        rldly.flagver = flagVer
        rldly.refant  = refAnt
        rldly.solint  = dataInt
        if debug:
            print("timerange", rldly.timerang)
            rldly.i
        # Trap failure
        try:
            if not check:
                rldly.g
        except Exception as exception:
            print(exception)
            mess = "rldly Failed retCode="+str(rldly.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
        # Get new CL table number
        if not check:
            # Open and close image to sync with disk
            uv.Open(UV.READONLY, err)
            uv.Close(err)
            gainUse = uv.GetHighVer("AIPS CL")

    # end R-L delay cal

    # R-L phase cal
    if RLPCal!=None:
        ncal = len(RLPCal)  # How many calibrators?
        img = ObitTask.ObitTask("Imager")
        try:
            img.userno     = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        img.taskLog    = logfile
        if not check:
            setname(uv,img)
        img.doCalib    = doCalib
        img.gainUse    = gainUse
        img.flagVer    = flagVer
        img.doPol      = True
        img.Stokes     = "IQU"
        img.FOV        = FOV
        img.Niter      = niter
        img.autoWindow = True
        img.dispURL    = "None"
        img.Catalog    = "None"
        img.nThreads   = nThreads
        img.noScrat    = noScrat
        img.prtLv      = 2
        # Temporary output files
        if img.DataType=="AIPS":
            img.outName = "TEMP"
            img.outClass= "IPOLCL"
            img.outDisk = img.inDisk
            img.outSeq  = 6666
            img.out2Name = "TEMP"
            img.out2Class= "IPOLCL"
            img.out2Disk = img.inDisk
            img.out2Seq  = 7777
        elif img.DataType=="FITS":
            img.outFile  = "TEMPPOLCAL.fits"
            img.outDisk  = img.inDisk
            img.out2File = "TEMPPOLCAL2.uvtab"
            img.out2Disk = img.inDisk

        # How many IFs?
        if not check:
            h = uv.Desc.Dict
            if h["jlocif"]>=0:
                nif = h["inaxes"][h["jlocif"]]
            else:
                nif = 1
        else:
            nif = 1


        # Loop over calibrators
        SouCal = []
        for ical in range (0,ncal):
            img.Sources[0]= RLPCal[ical][0]
            #rlpass.RLPhase   = RLPCal[ical][1]
            #rlpass.RM        = RLPCal[ical][2]
            # Loop over IF imaging I,Q, U
            # Lists of flux densities and RMSes
            IFlux = []
            IRMS  = []
            QFlux = []
            QRMS  = []
            UFlux = []
            URMS  = []
            for iif in range (1, nif+1):
                img.BIF = iif
                img.EIF = iif
                #img.dispURL    = "ObitView"  # DEBUG
                #img.debug=True               # DEBUG
                if debug:
                    img.i
                    img.debug = debug
                # Trap failure
                try:
                    if not check:
                        img.g
                except Exception as exception:
                    print(exception)
                    mess = "Imager Failed retCode="+str(img.retCode)
                    printMess(mess, logfile)
                    return 1
                else:
                    pass

                if check:      # Don't bother if only checking
                    continue
                # Get fluxes from Summed CCs, RMS from inner quarter of images
                if img.DataType=="AIPS":
                    outName = (img.Sources[0].strip()+"TEMP")[0:12]
                    outDisk = img.outDisk
                    outSeq  = 6666
                    # Stokes I
                    outClass="IPOLCL"
                    x =  Image.newPAImage("I",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    h = x.Desc.Dict
                    blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                    trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    IFlux.append(SumCC)
                    IRMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # Stokes Q
                    outClass="QPOLCL"
                    x =  Image.newPAImage("Q",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    QFlux.append(SumCC)
                    QRMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # Stokes U
                    outClass="UPOLCL"
                    x =  Image.newPAImage("U",outName[0:12], outClass[0:6], outDisk,outSeq,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    UFlux.append(SumCC)
                    URMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # Delete UV output
                    out2Name = (img.Sources[0].strip()+"TEMP")[0:12]
                    out2Class="IPOLCL"
                    out2Disk = img.inDisk
                    out2Seq  = 7777
                    u =  UV.newPAUV("UV",out2Name,out2Class,out2Disk,out2Seq,True,err)
                    u.Zap(err)
                    del u
                elif img.DataType=="FITS":
                    # Stokes I
                    outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                    x =  Image.newPFImage("I",outFile,img.outDisk,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    h = x.Desc.Dict
                    blc = [h["inaxes"][0]/4,h["inaxes"][1]/4]
                    trc = [3*h["inaxes"][0]/4,3*h["inaxes"][1]/4]
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    IFlux.append(SumCC)
                    IRMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # Stokes Q
                    outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                    x =  Image.newPFImage("Q",outFile,img.outDisk,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    QFlux.append(SumCC)
                    QRMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # Stokes U
                    outFile  = img.Sources[0].strip()+"ITEMPPOLCAL.fits"
                    x =  Image.newPFImage("Q",outFile,img.outDisk,True,err)
                    SumCC = EVLAGetSumCC (x,err)
                    stat = imstat(x, err, blc=blc,trc=trc, logfile=logfile)
                    UFlux.append(SumCC)
                    URMS.append(stat["RMSHist"])
                    x.Zap(err)  # Cleanup
                    del x
                    # out2File = img.Sources[0].strip()+"TEMPPOLCAL2.uvtab"
                    u =  UV.newPFUV("UV",outFile,img.outDisk,True,err)
                    u.Zap(err)
                    del u
               # End accumulate statistics by file type
            # End loop over IF
            # Save source info
            SouCal.append({"name":img.Sources[0],"Phase":RLPCal[ical][1],"RM":RLPCal[ical][2], \
                               "IFlux":IFlux, "IRMS":IRMS, "QFlux":QFlux, "QRMS":QRMS, \
                               "UFlux":UFlux, "URMS":URMS})
        # end loop over calibrators

        # Give results, weighted compute R-L correction
        import math
        mess = '\n R-L Phase calibration results'
        printMess(mess, logfile)
        RLCor = []
        RLCorRSum = []
        RLCorISum = []
        RLCorWt   = []
        # Zero accumulators
        for i in range (0,len(IFlux)):
            RLCorRSum.append(0.0)
            RLCorISum.append(0.0)
            RLCorWt.append(0.0)

        for ical in range (0,ncal):
            IFlux   = SouCal[ical]["IFlux"]
            IRMS    = SouCal[ical]["IRMS"]
            QFlux   = SouCal[ical]["QFlux"]
            QRMS    = SouCal[ical]["QRMS"]
            UFlux   = SouCal[ical]["UFlux"]
            URMS    = SouCal[ical]["URMS"]
            RLPhase = SouCal[ical]["Phase"]
            #Rotatation measure
            # RM      = SouCal[ical]["RM"]
            mess = SouCal[ical]["name"]+"\n IF     IFlux    IRMS    QFlux   QRMS    UFlux  URMS   R-L Corr     Wt"
            printMess(mess, logfile)
            for i in range (0,len(IFlux)):
                # REALLY NEED RM Correction!!!!!
                cor = RLPhase - 57.296 * math.atan2(UFlux[i],QFlux[i])
                if cor>180:
                    cor -= 360.0
                if cor<-180:
                    cor += 360.0
                wt = (QFlux[i]**2 + UFlux[i]**2) /(QRMS[i]**2 + URMS[i]**2)   # weight from SNR
                RLCorRSum[i] += (math.cos(cor/57.296)*wt)
                RLCorISum[i] += (math.sin(cor/57.296)*wt)
                RLCorWt[i]   += wt
                mess = "%3d  %8.3f %8.3f %7.3f %7.3f %7.3f %7.3f %8.3f %7.1f "% \
                    (i+1, IFlux[i], IRMS[i], QFlux[i], QRMS[i], UFlux[i], URMS[i], cor, wt)
                printMess(mess, logfile)
            # Copy gainUse to new highest CL table
            if not check:
                # Open and close image to sync with disk
                uv.Open(UV.READONLY, err)
                uv.Close(err)
                hiCL = uv.GetHighVer("AIPS CL")
            else:
                hiCL = 1
        # end loop over calibrators

        # Loop making weighted average correction
        mess = "\n\n Weighted average corrections\n IF  R-L Corr"
        printMess(mess, logfile)
        for i in range (0,len(IFlux)):
            if RLCorWt[i]>0.0:
                corr = RLCorRSum[i]
                cori = RLCorISum[i]
                cor = math.atan2(cori,corr)*57.296
            else:
                cor = 0.0
            mess = "%3d  %7.3f "% (i+1, cor)
            printMess(mess, logfile)
            RLCor.append(cor)
        # end loop making weighted average

        # If calibrating second uv data, copy AN table 1
        if uv2:
            # z = uv2.ZapTable("AIPS AN",1,err)
            EVLACopyTable (uv, uv2, "AIPS AN", err, \
                           logfile=logfile, check=check, debug=debug)
            if err.isErr:
                print("Error copying AN Table")
                return 1

        # Copy CL table to be modified (CLCOR buggy)
        if not check:
            EVLACopyTable (uv, uv, "AIPS CL", err, inVer=hiCL, outVer=hiCL+1, \
                           logfile=logfile, check=check, debug=debug)
        if err.isErr:
            print("Error copying CL Table")
            return 1

        # Apply R-L phase corrections
        clcor = AIPSTask.AIPSTask("clcor")
        try:
            clcor.userno   = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        clcor.logFile  = logfile
        if not check:
            setname(uv,clcor)
        clcor.opcode   = "POLR"
        clcor.gainver  = hiCL+1
        clcor.gainuse  = hiCL+1
        clcor.clcorprm[1:] = RLCor
        if debug:
            clcor.i
            clcor.debug = debug
        # Trap failure
        try:
            if not check:
                clcor.g
        except Exception as exception:
            print(exception)
            mess = "CLCOR Failed retCode="+str(clcor.retCode)
            printMess(mess, logfile)
            return 1
        else:
            pass
        # If calibrating second uv data, run clcor
        if uv2:
            mess = "Also calibrate Secondary UV data"
            printMess(mess, logfile)
            if not check:
                setname(uv2,clcor)
                # Open and close image to sync with disk
                uv2.Open(UV.READONLY, err)
                uv2.Close(err)
                hiCL = uv2.GetHighVer("AIPS CL")
                # Copy CL table to be modified (CLCOR buggy)
                EVLACopyTable (uv, uv, "AIPS CL", err, inVer=hiCL, outVer=hiCL+1, \
                               logfile=logfile, check=check, debug=debug)
                if err.isErr:
                    print("Error copying CL Table")
                    return 1

                clcor.gainver  = hiCL+1
                clcor.gainuse  = hiCL+1
            if debug:
                clcor.i
                clcor.debug = debug
            # Trap failure
            try:
                if not check:
                    clcor.g
            except Exception as exception:
                print(exception)
                mess = "CLCOR Failed retCode="+str(clcor.retCode)
                printMess(mess, logfile)
                return 1
            else:
                pass
        # end R-L Cal
    return 0
    # end EVLARLCal2

def EVLAReportTargets(uv, err,  FreqID=1, Sources=None, seq=1, sclass="IClean", \
                          Stokes="I", logfile='', check=False, debug=False):
    """
    Generate report info for a list of targets in AIPS files

    Returns a report which is a list of dicts, each of which contains

    ===========  ==========================================
    "Source"     Source name
    "haveImage"  True if images were made,
    "ObsDate"    Observing date as "yyyy-mm-dd"
    "numVis"     Number of visibilities (ignoring flagging)
    "Exposure"   Total integration time (day)
    "RA"         Source RA (deg) at standard equinox
    "Dec"        Source Dec (deg) at standard equinox
    "IFlux"      Source Table IPol flux per IF
    "QFlux"      Source Table QPol flux per IF
    "UFlux"      Source Table UPol flux per IF
    "VFlux"      Source Table VPol flux per IF
    ===========  ==========================================

    following present if haveImage True

    ========  ==============================================
    "RAPnt"   Antenna pointing RA (deg) at standard equinox
    "DecPnt"  Antenna pointing Dec (deg) at standard equinox
    "Freq"    Reference frequency (Hz)
    "BW"      Image bandwidth (Hz)
    "Size"    Width of image in deg (From Stokes I)
    "Cells"   Cell spacing in deg (From Stokes I)
    ========  ==============================================

    for each s in Stokes:

    =======  ===============================
    "sSum"   Sum of clean components in Jy
    "sPeak"  Peak pixel brightness in Jy
    "sRMS"   RMS noise in inner quarter (Jy)
    "sBeam"  Beam (maj, min, PA) (deg)
    =======  ===============================

    * uv         = UV data object
    * err        = Python Obit Error/message stack
    * Sources    = Source name or list of names to use
      If an empty list all sources in uv are included
    * seq        = sequence number of images
    * sclass     = Image class, first character replaced with char in Stokes
    * FreqID     = Frequency group identifier
    * Stokes     = Stokes parameters of images
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input
    """
    ################################################################
    mess = "Generate source statistics "
    printMess(mess, logfile)

    # If list empty get all sources
    if type(Sources)==list:
        sl = Sources
    else:
        sl = [Sources]

    if len(sl)<=0:
        slist = EVLAAllSource(uv,err,logfile=logfile,check=check,debug=debug)
    else:
        slist = sl

    # Init output
    Report = []

    # Image disk assumed same as uv
    disk = uv.Disk
    user = OSystem.PGetAIPSuser()

    # Loop over slist
    hd = uv.Desc.Dict
    for sou in slist:
        sdict = {"Source":sou, "haveImage":False}  # Init source structure
        sdict["ObsDate"]  = uv.Desc.Dict["obsdat"]
        # Observing stats
        obstat = EVLAGetTimes (uv, sou, err, logfile=logfile, check=check, debug=debug)
        sdict["numVis"]   = obstat["numVis"]
        sdict["Exposure"] = obstat["Exposure"]
        sdict["RA"]       = obstat["RA"]
        sdict["Dec"]      = obstat["Dec"]
        sdict["IFlux"]    = obstat["IFlux"]
        sdict["QFlux"]    = obstat["QFlux"]
        sdict["UFlux"]    = obstat["UFlux"]
        sdict["VFlux"]    = obstat["VFlux"]
        # Test if image exists
        cno = AIPSDir.PTestCNO(disk, user, sou, Stokes[0:1]+sclass[1:], "MA", seq, err)
        if cno <= 0 :
            Report.append(sdict)  # Save source info
            continue
        # Image statistics, loop over Stokes
        for s in Stokes:
            klass = s+sclass[1:]
            x = Image.newPAImage(s, sou, klass, disk, seq, True, err)
            hd = x.Desc.Dict
            sdict[s+"Beam"] = (hd["beamMaj"],hd["beamMin"],hd["beamPA"])
            # Some from Stokes I only
            if s == 'I':
                sdict["haveImage"] = True
                sdict["Size"]    = hd["inaxes"][1]*hd["cdelt"][1]
                sdict["Cells"]   = hd["cdelt"][1]
                sdict["RAPnt"]   = hd["obsra"]
                sdict["DecPnt"]  = hd["obsdec"]
                sdict["Freq"]    = hd["crval"][hd["jlocf"]]
                sdict["BW"]      = hd["cdelt"][hd["jlocf"]]
            blc = [hd["inaxes"][0]/4,hd["inaxes"][1]/4]
            trc = [3*hd["inaxes"][0]/4,3*hd["inaxes"][1]/4]
            stat = imstat(x,err,blc=blc,trc=trc)  # Image statistics inner quarter
            if abs(stat["Max"]) >  abs(stat["Min"]):
                sdict[s+"Peak"] = stat["Max"]
            else:
                sdict[s+"Peak"] = stat["Min"]
            sdict[s+"RMS"]  = stat["RMSHist"]
            sdict[s+"Sum"]  = EVLAGetSumCC(x, err, logfile=logfile, check=check, debug=debug)
            del x
        # End stokes image loop
        Report.append(sdict)  # Save source info
    # end loop over sources

    # Give terse listing
    if hd:
        mess = "\n Summary at frequency = "+"%8.3f"%(hd["crval"][hd["jlocf"]]*1.0e-9)+" GHz on "+ \
               uv.Desc.Dict["obsdat"]
        printMess(mess, logfile)
    for sdict in Report:
        mess = "\n Source = "+sdict["Source"]+", Exposure="+"%5.3f"%(sdict["Exposure"]*24.)+" hr"
        printMess(mess, logfile)
        if "IBeam" in sdict:
            mess = "IPol Beam = ("+"%8.3f"%(sdict["IBeam"][0]*3600.0)+", %8.3f"%(sdict["IBeam"][1]*3600.0)+ \
                   ", %6.1f"%(sdict["IBeam"][2])+") asec, asec, deg"
            printMess(mess, logfile)
        else:
            continue   # Nothing to report
        # Source table flux densities
        if "IFlux" in sdict:
            n = len(sdict["IFlux"])
            for i in range(0,n):
                mess = "IF "+str(i+1)+" IPol="+"%8.4f"%(sdict["IFlux"][i])+ \
                       ", QPol="+"%8.4f"%(sdict["QFlux"][i])+ \
                       ", UPol="+"%8.4f"%(sdict["UFlux"][i])+ \
                       ", VPol="+"%8.4f"%(sdict["VFlux"][i])
                printMess(mess, logfile)
        for s in Stokes:
            mess = "Stokes "+s+" Sum CC="+"%8.4f"%(sdict[s+"Sum"])+", Peak="+"%8.4f"%(sdict[s+"Peak"])+ \
                ", RMS="+"%8.5f"%(sdict[s+"RMS"])+" Jy"
            printMess(mess, logfile)
        # Polarization
        if Stokes=="IQU":
            ppolSum  = (sdict["QSum"]**2  + sdict["USum"]**2)**0.5
            ppolPeak = (sdict["QPeak"]**2 + sdict["UPeak"]**2)**0.5
            RLSum    = 57.296*math.atan2(sdict["USum"], sdict["QSum"])
            RLPeak   = 57.296*math.atan2(sdict["UPeak"],sdict["QPeak"])
            mess = "Sum CC PPol="+"%8.4f"%(ppolSum)+", R=L Phase="+"%8.2f"%(RLSum)+ \
                   "; Peak PPol="+"%8.4f"%(ppolPeak)+", R=L Phase="+"%8.2f"%(RLPeak)
            printMess(mess, logfile)
    # End terse listing
    return Report
    # end EVLAReportTargets

def EVLAGetSumCC(image, err, CCver=1,
                 logfile='', check=False, debug=False):
    """
    Sum fluxes in a CC table

    Sums the flux densities in a CC Table on an image
    Returns sum
    Returns with err set on error

    * image      = Image with CC table
    * err        = Python Obit Error/message stack
    * CCver      = CC table to sum
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    if check:
        return 0.0
    if debug:
        return 0.0
    # Open and close image to sync with disk
    image.Open(Image.READONLY, err)
    image.Close(err)
    # Anything there?
    ver = image.GetHighVer("AIPS CC")
    if ver<1:
        return 0.0
    CCTab = image.NewTable(Table.READONLY, "AIPS CC", CCver, err)
    if err.isErr:
        return 0.0
    # Open
    CCTab.Open(Table.READONLY, err)
    if err.isErr:
        return 0.0
    # Number of rows
    nrow    = CCTab.Desc.Dict["nrow"]
    sum     = 0.0
    # Loop over table
    for irow in range (1, nrow+1):
        CCrow = CCTab.ReadRow(irow, err)
        if err.isErr:
            return sum
        sum += CCrow["FLUX"][0]
    # End loop over table
    # Close table
    CCTab.Close(err)
    if err.isErr:
        return sum
    return sum
    # end EVLAGetSumCC

def EVLAGetTimes(uv, Source, err,
                 logfile='', check=False, debug=False):
    """
    Lookup observing times and number of visibilities for a source, other info

    Return dict {"numVis":no vis, "Exposure":Total integration time (day),
                 "RA": RA@equinox, "Dec" Dec@equinox,
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}

    * uv         = UV data with AIPS SU and AIPS NX tables
    * Source     = Source to lookup
    * err        = Python Obit Error/message stack
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    if check:
        return {"numVis":0, "Exposure":0.0, "RA":0.0, "Dec":0.0}
    # Open and close uv to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)

    # Lookup Source ID (SouID)
    SUtab = uv.NewTable(Table.READONLY, "AIPS SU", 1, err)
    SUtab.Open(Table.READONLY, err)
    if err.isErr:
        return  {"numVis":0, "Exposure":0.0, "RA":0.0, "Dec":0.0}
    # Number of rows
    nrow =  SUtab.Desc.Dict["nrow"]
    for i in range (0,nrow):    # Loop over rows
        SUrow = SUtab.ReadRow(i+1, err)
        if err.isErr:
            return  {"numVis":0, "Exposure":0.0, "RA":0.0, "Dec":0.0}
        SouID = SUrow["ID. NO."][0]
        RA    = SUrow["RAEPO"][0]
        Dec   = SUrow["DECEPO"][0]
        IFlux = SUrow["IFLUX"]
        QFlux = SUrow["QFLUX"]
        UFlux = SUrow["UFLUX"]
        VFlux = SUrow["VFLUX"]
        #if debug:
        #    mess="Source "+Source+" test "+SUrow["SOURCE"][0]+" ID ="+str(SouID)+ \
        #        " match="+str(SUrow["SOURCE"][0].rstrip()==Source.rstrip())
        #    printMess(mess, logfile)
        if SUrow["SOURCE"][0].rstrip()==Source.rstrip():   # This it?
            break;
    SUtab.Close(err)
    if err.isErr:
        return  {"numVis":0, "Exposure":0.0, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}

    # get observing stats from AIPS NX table
    cntVis  = 0
    sumTime = 0.0
    NXTab = uv.NewTable(Table.READONLY, "AIPS NX", 1, err)
    if err.isErr:
        return {"numVis":0, "Exposure":0.0, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}
    # Open
    NXTab.Open(Table.READONLY, err)
    if err.isErr:
        return {"numVis":cntVis, "Exposure":sumTime, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}
    # Number of rows
    nrow    = NXTab.Desc.Dict["nrow"]
    # Loop over table
    for irow in range (1, nrow+1):
        NXrow = NXTab.ReadRow(irow, err)
        if err.isErr:
            return {"numVis":cntVis, "Exposure":sumTime, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}
        #  Is this the desired source?
        if NXrow["SOURCE ID"][0]==SouID:
            sumTime += NXrow["TIME INTERVAL"][0]
            cntVis  += NXrow["END VIS"][0] - NXrow["START VIS"][0] + 1
    # End loop over table
    # Close table
    NXTab.Close(err)
    if err.isErr:
        return {"numVis":cntVis, "Exposure":sumTime, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}

    if debug:
        mess="EVLAGetTimes: Source "+Source+"="+str(SouID)+" numVis="+str(cntVis)+ \
            " Integration time = "+"%5.3f"%(sumTime*24.)+" hr"
        printMess(mess, logfile)

    return {"numVis":cntVis, "Exposure":sumTime, "RA":RA, "Dec":Dec, \
                 "IFlux":IFlux, "QFlux":QFlux, "UFlux":UFlux, "VFlux":VFlux}
    # end EVLAGetTimes

def KATImageTargets(uv, err, Sources=None,  FreqID=1, seq=1, sclass="IClean", band="", \
                     doCalib=-1, gainUse=0, doBand=-1, BPVer=0,  flagVer=-1,  OutlierArea=5.0, \
                     doPol=False, PDVer=-1,  minFlux=0.0, nx=[0], ny=[0], \
                     xCells=0, yCells=0, Reuse=0.0, minPatch=0, OutlierSize=0, noNeg=False, \
                     Stokes="I", FOV=0.1/3600.0, Robust=0, Niter=300, CleanRad=None, \
                     maxPSCLoop=0, minFluxPSC=0.1, solPInt=20.0/60., \
                     solPMode="P", solPType= "  ", CCVer=-1, CGain=0.1, \
                     maxASCLoop=0, minFluxASC=0.5, solAInt=2.0, \
                     solAMode="A&P", solAType= "  ", autoCen=False, \
                     avgPol=False, avgIF=False, minSNR = 5.0, refAnt=0, \
                     do3D=True, BLFact=0.999, BLchAvg=False, doOutlier=None, \
                     doMB=False, norder=2, maxFBW=0.05, doComRes=True, \
                     PBCor=True, antSize=12.0, nTaper=0, Tapers=[20.0], \
                     sefd=500.0,
                     nThreads=1, noScrat=[], logfile='', check=False, debug=False):
    """
    Image a list of sources with optional selfcal

    Uses Imager or MFImage to image a list of sources.
    Data must be at least approximately calibrated
    Returns task error code, 0=OK, else failed

    * uv         = UV data object
    * err        = Python Obit Error/message stack
    * Sources    = Source name or list of names to use
      If an empty list all sources in uv are included
    * seq        = sequence number of output
    * sclass     = Image output class
    * band       = project band - appended to name
    * FreqID     = Frequency group identifier
    * doCalib    = Apply calibration table
    * gainUse    = CL/SN table to apply
    * doBand     = If >0.5 apply bandpass cal.
    * BPVer      = Bandpass table version
    * flagVer    = Input Flagging table version
    * doPol      = Apply polarization cal?
    * PDVer      = PD version for pol cal, -1=>use IF
    * minFlux    = minimum flux density for initial CLEAN
    * Stokes     = Stokes parameters to image
    * FOV        = Field of view to image in deg
    * Robust     = Weighting robustness parameter
    * Niter      = max no. iterations
    * xCells     = x-axis cell size in arcsec
    * yCells     = y-axis cell size in arcsec
    * CleanRad   = CLEAN radius about center or None=autoWin
    * maxPSCLoop = max. number of phase sc loops
    * minFluxPSC = Trip level for phase self cal (Jy)
    * solPInt    = Phase solution interval (min)
    * solPMode   = Phase soln mode "P", "DELA"
    * solPType   = Phase soln type
    * maxASCLoop = max. number of amp&phase sc loops
    * minFluxASC = Trip level for amp&phase self cal (Jy)
    * solAInt    = Amp&phase solution interval (min)
    * solAMode   = Amp&Phase soln mode "A&P", "P", "DELA"
    * solAType   = Amp&PPhase soln type
    * avgPol     = Average poln in SC?
    * avgIF      = Average IFs in SC?
    * minSNR     = minimum acceptable SNR in SC
    * refAnt     = Reference antenna
    * do3D       = Use 3D imaging?
    * doComRes   = Force common resolution in frequency? (MF)
    * BLFact     = Baseline dependent averaging factor
    * BLchAvg    = If True and BLFact>=1.0 also average channels
    * doOutlier  = Outliers from NVSS?  Yes=> 4*FOV, 10 mJy >1 GHz else 50 mJy
                   None = Default, Yes if freq<6 GHz
    * doMB       = If True is wideband imaging
    * norder     = order on wideband imaging
    * maxFBW     = max. fractional wideband imaging
    * PBCor      = Do PB correction on final image?
    * antSize    = antenna size (m) for PBCor
    * nTaper     = number of (additional) multi resolution tapers
    * Tapers     = Sizes of additional tapers in pixels
    * nThreads   = Max. number of threads to use
    * noScrat    = list of disks to avoid for scratch files
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input
    """
    ################################################################
    mess = "Image a list of sources "
    printMess(mess, logfile)

    # Tolerate missing BP table
    # Open and close image to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)
    hiBP = uv.GetHighVer("AIPS BP")
    if hiBP<=0:
        doBand = -1
    # get reference Freq
    refFreq = uv.Desc.Dict["crval"][uv.Desc.Dict["jlocf"]]
    bandwidth = abs(uv.Desc.Dict["cdelt"][uv.Desc.Dict["jlocf"]]*uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocf"]])
    # If list empty get all sources
    if type(Sources)==list:
        sl = Sources
    else:
        sl = [Sources]

    if len(sl)<=0:
        slist = EVLAAllSource(uv,err,logfile=logfile,check=check,debug=debug)
    else:
        slist = sl
    if doMB:
        imager = ObitTask.ObitTask("MFImage")
        try:
            imager.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
        imager.norder = norder
        imager.maxFBW = maxFBW
        imager.prtLv = 2
    else:
        imager = ObitTask.ObitTask("Imager")
        imager.prtLv = 2
        try:
            imager.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
        except Exception as exception:
            pass
    imager.taskLog  = logfile
    if not check:
        setname(uv,imager)
    imager.outDisk     = imager.inDisk
    #imager.outName     = "_"+band
    imager.out2Name    = "_"+band
    imager.out2Disk    = imager.inDisk
    imager.outSeq      = seq
    imager.out2Seq     = seq
    imager.outClass    = sclass
    imager.BLFact      = BLFact
    imager.BLchAvg     = BLchAvg
    imager.flagVer     = flagVer
    imager.doCalib     = doCalib
    imager.gainUse     = gainUse
    imager.doBand      = doBand
    imager.BPVer       = BPVer
    imager.doPol       = doPol
    if "PDVer" in imager.__dict__:
        imager.PDVer = PDVer
    imager.Stokes      = Stokes
    imager.FOV         = FOV
    imager.Robust      = Robust
    imager.Niter       = Niter
    imager.CCVer       = CCVer
    imager.Gain        = CGain
    imager.maxPSCLoop  = maxPSCLoop
    imager.solPInt     = solPInt
    imager.solPMode    = solPMode
    imager.solPType    = solPType
    imager.maxASCLoop  = maxASCLoop
    imager.solAInt     = solAInt
    imager.solAMode    = solAMode
    imager.solAType    = solAType
    imager.avgPol      = avgPol
    imager.avgIF       = avgIF
    imager.refAnt      = refAnt
    imager.minSNR      = minSNR
    imager.do3D        = do3D
    imager.dispURL     = "None"
    imager.PBCor       = PBCor
    imager.antSize     = antSize
    imager.nTaper      = nTaper
    imager.Tapers      = Tapers
    imager.xCells      = xCells
    imager.yCells      = yCells
    imager.nx          = nx
    imager.ny          = ny
    imager.noNeg       = noNeg
    imager.Reuse       = Reuse
    imager.minPatch    = minPatch
    imager.OutlierSize = OutlierSize
    imager.doGPU       = True
    if doOutlier or ((doOutlier==None) and refFreq<6.0e9):
        imager.OutlierDist = FOV*OutlierArea   # Outliers from NVSS/SUMMS for lower frequencies
        if refFreq>1.0e9:
            imager.OutlierFlux = 0.002
        else:
            imager.OutlierFlux = 0.002
    # Auto window or centered box
    if CleanRad:
        imager.CLEANBox=[-1,CleanRad,0,0]
    else:
        imager.autoWindow  = True
    if "doComRes" in imager.__dict__:
        imager.doComRes  = doComRes
    imager.doComRes = True
    imager.noScrat     = noScrat
    imager.nThreads    = nThreads
    imager.prtLv = 5
    #imager.MFTaper = 
    #imager.i
    imager.debug = True
    if debug:
        imager.prtLv = 5
        imager.i
        imager.debug = debug
    OK = False   # Some must work
    # Loop over slist
    for sou in slist:
        sou=sou.replace(' ','_')         # Just in case a stray space in a source name has made it to here
        #suinfo = EVLAGetTimes(uv, sou, err, logfile=logfile, check=check,debug=debug)
        #if doOutlier or ((doOutlier==None) and refFreq<6.0e9):
            # Use NVSS north of dec 30 S and SUMMS southward
        #    if suinfo["Dec"]<-30.0:
        imager.Catalog = 'AllSkyVZ.FIT.gz'
        # Get the source parameters for this source
        #iflux=suinfo["IFlux"][0]
        iflux=0.0
        #exposuresec=suinfo["Exposure"]*3600.*24.
        #mindr=iflux/1500.0                       # Cutoff based on dynamic range of 1500:1
        #SEFD=1500                       # TODO: SEFD should be per antenna here
        #if exposuresec>0.0: thermNoise=SEFD/math.sqrt(exposuresec*bandwidth)
        #else: thermNoise=0.0
        # Cutoff cleaning at 2 times theoretical noise or minimum dynamic range.
        # Cutoff Phase self cal at 20.0sigma or 20mJy (conusion noise limit)
        # Cutoff Amp&Phase self cal at 500.0sigma or 500mJy
        if minFlux is None: imager.minFlux=max(2.0*thermNoise,mindr)
        else: imager.minFlux=minFlux
        if minFluxPSC is None: imager.minFluxPSC=max(20.0*thermNoise,0.02)
        else: imager.minFluxPSC=minFluxPSC
        if minFluxASC is None: imager.minFluxASC=max(500.0*thermNoise,0.5)
        else: imager.minFluxASC=minFluxASC
        # 1/3 the number of CC's for calibrators and narrow-band observations
        if iflux>0.0 or bandwidth<50e6:
            imager.Niter=int(Niter/3)
        else: imager.Niter=Niter
        # 3D imaging off for calibrators.
        if iflux>0.0:
            imager.do3D=False
        else:
            imager.do3D=False
        #imager.do3D=True
        #imager.minFlux=0.0
        #del suinfo
        # Test autoCen
        #if autoCen:
        imager.autoCen = 0.15 #max(100.0*thermNoise,0.1)
        #imager.PeelFlux = 0.3
        #imager.PeelLoop =2
        #imager.PeelRefAnt=refAnt
        #imager.PeelSNRMin=4.0
        #imager.PeelSolInt=4./60.
        #imager.PeelMode='A&P'
        #imager.PeelNiter=100
        #imager.PeelMinFlux=0.0
        #imager.PeelAvgPol=False
        #imager.PeelAvgIF=False
        imager.Sources[0] = sou
        mess = "Image "+sou
        printMess(mess, logfile)
        mess = "Stop at %4.2f mJy or %5d CCs" % (imager.minFlux*1000,imager.Niter)
        printMess(mess, logfile)
        # Trap failure
        try:
            if not check:
                imager.g
        except Exception as exception:
            print(exception)
            mess = "Imager Failed retCode= "+str(imager.retCode)
            printMess(mess, logfile)
            #return 1  Allow some failures
            # Cleanup image mess
            AllDest(err,Atype="MA",Aname=imager.Sources[0][0:12], disk=imager.outDisk, Aseq=imager.outSeq);
        else:
            OK = True
        #u = UV.newPAUV("Self-calibrated uv data", out2Name, out2Class, imager.out2Disk, imager.out2Seq, False, err)

        # delete Imager file if not debug
        if not debug:
            out2Name = imager.Sources[0].strip()+"_"+band
            out2Name = out2Name[0:12]
            if doMB:
                out2Class = "MFImage"
            else:
                out2Class = "Imager"
            # Tolerate failures
            try:
                # Test if file exists
                cno = AIPSDir.PTestCNO(imager.out2Disk, OSystem.PGetAIPSuser(), \
                                       out2Name, out2Class, "UV", imager.out2Seq, err)
                if cno>0:
                    u = UV.newPAUV("Self-calibrated uv data", out2Name, out2Class, imager.out2Disk, imager.out2Seq, False, err)
                    #Save self-calibrated vis to disk
                    filename = sou+'_selfCal.uv'
                    KATSplatandUVFITS(u, filename, 0, err, logfile=logfile)

                    #KATUVFITS(u, filename, 0, err, exclude=["AIPS HI", "AIPS SL", "AIPS PL"], include=["AIPS AN", "AIPS FQ"], compress=False, logfile=logfile)
                    filename = sou+'_selfCal.uvtab'
                    KATUVFITab(u, filename, 0, err)
                    #KATSplatandUVFITS(u, sou+'_selfCal.uv', 0, err, logfile=logfile)
                    if UV.PIsA(u):
                        u.Zap(err) # cleanup
                    if err.isErr:
                        mess = "Error deleting Imager work file"
                        printMess(mess, logfile)
                        #return 1
                    del u
            except Exception as exception:
                print(exception)
                mess = "Imager Cleanup Failed source= "+imager.Sources[0].strip()+"_"+band
                printMess(mess, logfile)
                OErr.PClear(err)     # Clear any message/error
                #return 1  Allow some failures
            else:
                pass
    # end loop over sources
    # Something work?
    if not OK:
        printMess("All images failed", logfile)
        return 1

    return
    # end EVLAImageTargets


def EVLAAllSource(uv, err, \
               logfile='', check=False, debug=False):
    """
    Returns List of all sources, empty if no SU table

    * uv         = UV data object
    * err        = Python Obit Error/message stack
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    # Open and close uv to sync with disk
    uv.Open(UV.READONLY, err)
    uv.Close(err)

    allSou = []
    if check:
        return allSou
    # Is there an SU table?
    hiver = uv.GetHighVer("AIPS SU")
    if hiver<=0:
        printMess("No SoUrce table found", logfile)
        return allSou
    mess = "List of sources in database"
    printMess(mess, logfile)
    SUTab = uv.NewTable(Table.READONLY, "AIPS SU", 1, err)
    if err.isErr:
        return allSou
    # Open
    SUTab.Open(Table.READONLY, err)
    if err.isErr:
        return allSou
    # Number of rows
    nrow =  SUTab.Desc.Dict["nrow"]
    if debug:
        mess = str(nrow)+" sources in database"
        printMess(mess, logfile)
    for i in range (0,nrow):    # Loop over rows
        SUrow = SUTab.ReadRow(i+1, err)
        if err.isErr:
            return
        allSou.append(SUrow["SOURCE"][0].strip())
        mess = "Source("+str(i+1)+") = "+SUrow["SOURCE"][0]
        printMess(mess, logfile)
    # end loop over rows

    # Close table
    SUTab.Close(err)
    if err.isErr:
        return allSou
    return allSou
    # end EVLAAllSource

def EVLAPlotTab(uv, inext, invers, err, \
                source=None, timerang=[0.,0.,0.,0.,0.,0.,0.,0.], \
                stokes="HALF", optype="    ", opcode="    ", nplots=1,  \
                logfile=None, check=False, debug=False):
    """
    Makes AIPS plots of tables

    Returns task error code, 0=OK, else failed

    * uv       = UV data object to plot
    * inext    = AIPS Table ("SN", "CL", "TY", "PC")
    * inver    = version number, 0-> highest
    * source   = if given the name of the source
    * timerang = timerange to plot.
    * stokes   = Stokes type to plot
    * optype   = Data to be plotted (see help snplt)
    * opcode   = Plot type (see help snplt)
    * nplots   = number of plots per page
    * err      = Obit error/message stack
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = show input
    """
    ################################################################
    snplt = AIPSTask.AIPSTask("snplt")
    try:
        snplt.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv,snplt)
    snplt.inext   = inext
    snplt.invers  = invers
    snplt.optype  = optype
    snplt.opcode  = opcode
    snplt.nplots  = nplots
    snplt.stokes  = stokes
    snplt.msgkill = 5        # Suppress blather
    i = 1
    for t in timerang:
        snplt.timerang[i] = t
        i  += 1
    snplt.logFile = logfile
    if debug:
        snplt.i
    # Trap failure
    try:
        if not check:
            snplt.g
    except Exception as exception:
        print(exception)
        mess = "SNPLT Failed "
        printMess(mess, logfile)
        return 1
    else:
        pass

    # Open/close UV to update header
    if not check:
        uv.Open(UV.READONLY,err)
        uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1

    return 0
    # end EVLAPlotTab

def EVLAWritePlots(uv, loPL, hiPL, plotFile, err, \
                   plotDesc="Diagnostic plot", \
                   logfile=None, check=False, debug=False):
    """
    Writes plots to an external postscript file

    All Plots deleted from AIPS
    Returns task error code, 0=OK, else failed

    * uv       = UV data object to plot
    * loPL     = Lowest (1-rel) plot number
    * hiPL     = Highest PL version number (0->all)
    * plotFile = plot file
    * err      = Obit error/message stack
    * plotDesc = Description of plot
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = show input
    """
    ################################################################
    # Open/close UV to update header
    if not check:
        uv.Open(UV.READONLY,err)
        uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1
    if hiPL<=0 and not check:
        hiPL = uv.GetHighVer("AIPS PL")

    lwpla = AIPSTask.AIPSTask("lwpla")
    try:
        lwpla.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv,lwpla)
    lwpla.plver   = max(1, loPL)
    lwpla.invers  = hiPL
    lwpla.outfile = plotFile
    lwpla.logFile = logfile
    lwpla.msgkill = 5         # Suppress blather - as much as possible
    if debug:
        lwpla.i
    # Trap failure
    try:
        if not check:
            lwpla.g
    except Exception as exception:
        print(exception)
        mess = "Lwpla Failed - continuing anyway"
        printMess(mess, logfile)
        # return 1  # Continue in spite of lwpla failure
    else:
        if os.path.exists(plotFile):    # May not exist
            EVLAAddOutFile(plotFile, 'project', plotDesc, logFile=logfile)

    # Delete plot files
    if not check:
        uv.ZapTable("AIPS PL", -1,err)

    return 0
    # end EVLAWritePlots

def KATSpecPlot(uv, Source, timerange, maxgap, refAnt, err, Stokes=["RR","LL"], \
                 doband=0, plotFile="./spec.ps", doPol=False, PDVer=-1,  \
                 check=False, docalib=2, debug=False, logfile = ""):
    """
    Plot amplitude and phase across the spectrum.

    returns scratch file with plot
    Note: possm can't apply flags so data copied to scratch file
    Returns task error code, 0=OK, else failed

    * uv        = uv data object
    * Source    = List of sources to plot
    * timerange = timerange (Obit form) to plot
    * maxgap    = Gap length in seconds to split scans for NX index
    * refAnt    = ref. Ant, only baselines to this antenna plotted
    * err       = Obit error object
    * Stokes    = List of stokes types to plot
    * doband    = do bandpass calibration before plotting (requires BP table)
    * doPol     = Apply polarization cal?
    * PDVer     = PD version for pol cal, -1=>use IF
    * plotFile  = name of output PS file
    * check     = Only check script, don't execute tasks
    * debug     = Run tasks debug, show input
    * logfile   = Log file for task
    """
    # Open/close UV to update header
    if not check:
        uv.Open(UV.READONLY,err)
        uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return None
    # Calibrate and edit data
    scr  = uv.Scratch(err)
    info = uv.List
    info.set("doCalSelect", True)
    info.set("doCalib", docalib)
    info.set("gainUse", 0)
    info.set("doBand", doband)
    info.set("BPVer", 0)
    info.set("flagVer", 0)
    info.set("Sources", Source)
    info.set("Stokes", "    ")
    info.set("timeRange", timerange)
    if doPol:
        info.set("doPol", 1)
    else:
        info.set("doPol", 0)
    info.set("PDVer", PDVer)
    #uv.Header(err) # DEBUG
    # Trap failure
    try:
        uv.Copy(scr, err)
    except Exception as exception:
        print(exception)
        mess = "Copy plot data failed - continuing"
        printMess(mess, logfile)
        return None
    else:
        pass
    scr.Info(err)     # Get file information
    #Reindex the file
    UV.PUtilIndex(scr, err, maxGap=float(maxgap))
    info = uv.List

    # Reset selection
    info.set("doCalSelect",True)
    info.set("doCalib",-1)
    info.set("gainUse",0)
    info.set("doBand",-1)
    info.set("BPVer",0)
    info.set("flagVer",0)
    info.set("Sources",["     "])
    info.set("timeRange",[0.0, 0.0])
    info.set("doPol", 0)
    info.set("PDVer", -1)

    # If data labeled XY pol, relabel RR,LL... - POSSM cannot cope
    d = scr.Desc.Dict
    if d["crval"][d["jlocs"]]<-4:
        d["crval"][d["jlocs"]] = -1.0
        d["cdelt"][d["jlocs"]] = -1.0
        scr.Desc.Dict = d
        scr.UpdateDesc(err)

    # Setup and run POSSM
    possm = AIPSTask.AIPSTask("possm")
    try:
        possm.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    setname(scr, possm)
    if type(Source) is not list:
        source = [ Source ]           # get BP calibration source, in list format
    possm.sources= AIPSTask.AIPSList( Source )
    timerang = [ timerange[0],  0,   0,   0, timerange[1],  0,   0,   0 ]
    possm.timerang = AIPSTask.AIPSList( timerang )
    solint          = (timerange[1]-timerange[0])*1440.0
    possm.baseline[1] = refAnt
    possm.flagver  = -1           # POSSM can't flag
    possm.aparm    = AIPSTask.AIPSList( [0] * 10 ) # initialize with zeroes
    possm.aparm[1] = -1           # scalar average
    possm.aparm[9] = 3            # all IFs and pols in same frame
    possm.nplots   = 6            # plot each baseline in separate frame on page
    possm.ltype    = 3            # include all labels
    possm.solint   = -1 #solint       # time interval of plot
    possm.logFile  = logfile
    possm.msgkill  = 0          # Suppress blather as much as possible
    # Loop over Stokes
    for s in Stokes:
        possm.stokes   = s
        # Trap failure
        try:
            if not check:
                possm.g
        except Exception as exception:
            print(exception)
            mess = "POSSM Failed - continue anyway"
            printMess(mess, logfile)
            # return 1
        else:
            pass
        # End Stokes loop
    return scr
# end EVLASpecPlot

def EVLAApplyCal(uv, err, SNver=0, CLin=0, CLout=0, maxInter=240.0, \
                     logfile=None, check=False, debug=False):
    """
    Applies an SN table to a CL table and writes another

    Returns task error code, 0=OK, else failed

    * uv       = UV data object to clear
    * err      = Obit error/message stack
    * SNver    = SN table to apply, 0=>highest
    * CLin     = input CL table, 0=>highest
    * CLout    = output CL table, 0=>create new
    * maxInter = Max time (min) over which to interpolate
    * logfile  = logfile for messages
    * check    = Only check script, don't execute tasks
    * debug    = show input, ObitTasks debug
    """
    ################################################################
    # Open/close UV to update header
    if not check:
        uv.Open(UV.READONLY,err)
        uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1
    if not check:
        if SNver<=0:
            SNver = uv.GetHighVer("AIPS SN")
        if CLin<=0:
            CLin = uv.GetHighVer("AIPS CL")
        if CLout<=0:
            CLout = uv.GetHighVer("AIPS CL")+1

    if CLin<1:
        mess = "No input CL table to update"
        printMess(mess, logfile)
        uv.Header(err)
        return 1
    mess = "Update CL "+str(CLin)+" with SN "+str(SNver)+" to CL "+str(CLout)
    printMess(mess, logfile)

    clcal = ObitTask.ObitTask("CLCal")
    try:
        clcal.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uv,clcal)
    clcal.solnVer  = SNver
    clcal.calIn    = CLin
    clcal.calOut   = CLout
    clcal.maxInter = maxInter
    clcal.taskLog  = logfile
    clcal.debug    = debug
    if debug:
        clcal.i
    # Trap failure
    try:
        if not check:
            clcal.g
    except Exception as exception:
        print(exception)
        mess = "CLCal Failed retCode="+str(clcal.retCode)
        printMess(mess, logfile)
        return 1
    else:
        pass
    # End CLCal

    # Open/close UV to update header
    if not check:
        uv.Open(UV.READONLY,err)
        uv.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1

    return 0
    # end EVLAApplyCal

def EVLASpectrum(uv, plotSource, plotTime, maxGap, plotFile, refAnt, err, \
                 Stokes=["RR","LL"], doband=-1, docalib=2,           \
                 logfile=None, check=False, debug=False):
    """
    Spectrum plot of selected data

    Returns task error code, 0=OK, else failed

    * uv         = UV data object to clear
    * plotSource = Name of source to plot
    * plotTime   = timerange (Obit form) to plot
    * maxGap     = maximum gap in minutes to delineate scans 
    * plotFile   = name of output PS file
    * refAnt     = ref. Ant, only baselines to this antenna plotted
    * err        = Obit error/message stack
    * Stokes     = List of stokes types to plot
    * doband     = do bandpass calibration before plotting (requires BP table)
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input, ObitTasks debug
    """
    ################################################################
    # POSSM can't apply flags so write scratch file and plot
    scr = KATSpecPlot(uv, plotSource,  plotTime, maxGap, refAnt, err, \
                        Stokes=Stokes, doband=doband, docalib=docalib, \
                        plotFile=plotFile, check=check, logfile=logfile )
    retCode = 0
    if scr and scr.UVIsA():
        retCode = EVLAWritePlots(scr, 1, 0, plotFile, err, \
                                  plotDesc="Spectrum plots", \
                                  logfile=logfile, check=check, debug=debug)
    if retCode!=0:
        return 0   # tolerate failure
    if scr!=None:
        scr.Zap(err)
    return 0
    # end EVLASpectrum



def EVLAEditSNAmp(uv, SNver, err, \
                  sigma=20.0, FGver=-1, logfile='', check=False, debug=False):
    """
    Flag SN table entries with amplitudes discrepant from IF median

    For each IF in an SN table, the median amplitude and the RMS of
    the 80% amplitudes least different from the median are determined.
    Then SN table entries with amplitudes further from the median than
    sigma*RMS are flagged.
    Optionally adds entries to flag (FG) table
    Returns with err set on error

    * uv         = UV data object
    * SNver      = SN table to flag, 0=> highest
    * err        = Python Obit Error/message stack
    * sigma      = multiple of inner RMS different from median to flag
                   Should be pretty big
    * FGver      = FG table to add flags to, <=0 ->none
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    if SNver<=0:
        snver =  uv.GetHighVer("AIPS SN")
    else:
        snver = SNver;
    mess = "Edit SN table %d amplitudes by sigma %f" % (snver,sigma)
    printMess(mess, logfile)
    if FGver>0:
       mess = "Also write flagging entries in FG table %d" % (FGver)
       printMess(mess, logfile)
    # Get statistics
    stats = EVLASNAmpStats(uv, snver, err, \
                           logfile=logfile, check=check, debug=debug)
    if stats==[None] or err.isErr:
        mess = "Problem with SN table statistics"
        printMess(mess, logfile)
        return
    # Get Median RMS
    t = []
    for s in stats:
        if s!=None:
            t.append(s[1])
    RMS = t[len(t)//2]
    mess = "Median RMS %f" % (RMS)
    printMess(mess, logfile)
    # Set clipping levels
    cl = []
    iif = 1
    for s in stats:
        if s!=None:
            rang = [max(0.0,s[0]-sigma*RMS),s[0]+sigma*RMS]
            cl.append(rang)
            mess = "IF %d valid range = %s" % (iif,str(rang))
            printMess(mess, logfile)
        else:
            cl.append(None)
            mess = "IF %d: Too few data to edit" % (iif)
            printMess(mess, logfile)
        iif += 1;
    # Clip/flag
    EVLAClipSNAmp(uv, snver, cl, err,FGver=FGver,  \
                  logfile=logfile, check=check, debug=debug)
    if err.isErr:
        mess = "Problem with clipping SN table or flagging"
        printMess(mess, logfile)
        return
   # end EVLAEditSNAmp

def EVLAFlagFailSN(uv, SNver, err, \
                   FGver=-1, logfile='', check=False, debug=False):
    """
    Make entries in FG table for times of failed SN solutions

    Returns with err set on error

    * uv         = UV data object
    * SNver      = SN table to flag, 0=> highest
    * err        = Python Obit Error/message stack
    * FGver      = FG table to add flags to, <=0 ->none
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    if SNver<=0:
        snver =  uv.GetHighVer("AIPS SN")
    else:
        snver = SNver;
    mess = "Failed solutions in SN %d flagged in FG %d" % (snver,FGver)
    printMess(mess, logfile)
    fblank = FArray.PGetBlank() # Magic blanking value
    # Number of IFs
    nif   = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocif"]]
    # Number of Stokes
    npoln = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocs"]]
    SNTab = uv.NewTable(Table.READONLY, "AIPS SN", SNver, err, \
                        numIF=nif, numPol=npoln)
    if err.isErr:
        return
    # Open
    SNTab.Open(Table.READWRITE, err)
    if err.isErr:
        return
    # Number of rows
    nrow =  SNTab.Desc.Dict["nrow"]
    count = 0; total = 0
    for i in range (0,nrow):    # Loop over rows
        SNrow = SNTab.ReadRow(i+1, err)
        if err.isErr:
            return
        dirty = False
        # Loop over IF
        for iif in range (0, nif):
            total += 1
            if (SNrow["WEIGHT 1"][iif]<=0.0) or (SNrow["REAL1"][iif]==fblank):
                # Flag table?
                EVLAFlagSNClip(uv, SNrow, iif+1, 1, err, FGver=FGver, reason="Failed soln", \
                               logfile=logfile, check=check, debug=debug)
                count += 1
                dirty = True
            # Second Poln
            if npoln>1:
                total += 1
            if (npoln>1) and (SNrow["WEIGHT 2"][iif]<=0.0) or (SNrow["REAL2"][iif]==fblank):
                # Flag table?
                EVLAFlagSNClip(uv, SNrow, iif+1, 2, err, FGver=FGver, reason="Failed soln", \
                               logfile=logfile, check=check, debug=debug)
                count += 1
                dirty = True
       # Rewrite if modified
        if dirty and not check:
            SNTab.WriteRow(i+1, SNrow, err)
            if err.isErr:
                return
    # end loop over rows

    # Close table
    SNTab.Close(err)
    if err.isErr:
        return

    mess = "Flagged %d of total %d Gain entries" % (count, total)
    printMess(mess, logfile)
   # end EVLAFlagFailSN

def EVLASNAmpStats(uv, SNver, err, logfile='', check=False, debug=False):
    """
    Determine median and RMS of inner 80% of amplitude distribution per IF

    Returns with err set on error
    Return list:
        [(medn1, RMS1),...,(mednnumIF,RMDnumIF)]

    * uv         = UV data object
    * SNver      = SN table to flag
    * err        = Python Obit Error/message stack
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    fblank = FArray.PGetBlank() # Magic blanking value
    # Number of IFs
    nif   = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocif"]]
    # Number of Stokes
    npoln = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocs"]]
    npoln = min(2, npoln)   # No more than 2
    SNtab = uv.NewTable(Table.READONLY, "AIPS SN", SNver, err, \
                        numIF=nif, numPol=npoln)
    if err.isErr:
        return None
    # Open
    SNtab.Open(Table.READWRITE, err)
    if err.isErr:
        return None
    # Number of SN rows
    nrow =  SNtab.Desc.Dict["nrow"]
    # Initialize accumulators, 1 per IF
    # Each a list of amplitudes
    amps = []
    for i in range(0,nif):
        amps.append([])
    for i in range (0,nrow):    # Loop over rows
        SNrow = SNtab.ReadRow(i+1, err)
        if err.isErr:
            return None
        for iif in range(0,nif):
            if (SNrow["WEIGHT 1"][iif]>0.0) and (SNrow["REAL1"][iif]!=fblank):
                amp = (SNrow["REAL1"][iif]**2+SNrow["IMAG1"][iif]**2)**0.5
                amps[iif].append(amp)
            if (npoln>1) and (SNrow["WEIGHT 2"][iif]>0.0) and (SNrow["REAL2"][iif]!=fblank):
                amp = (SNrow["REAL2"][iif]**2+SNrow["IMAG2"][iif]**2)**0.5
                amps[iif].append(amp)
        # end IF loop
    # End loop over table

    # Close table
    SNtab.Close(err)
    if err.isErr:
        return None

   # Sort lists, get median, inner RMS
    out = []   # Initialize output
    for iif in range(0,nif):
        if len(amps[iif])>3:   # Need a min. amount of data
            amps[iif].sort()
            num  = len(amps[iif])
            medn = amps[iif][num//2]
            # inner half RMS about median
            b = num//10; e = 9*num//10;
            sum2 = 0.0; count = 0
            for i in range(b,e+1):
                val    = amps[iif][i]-medn
                sum2  += val*val
                count += 1
            RMS = (sum2/count)**0.5
            out.append((medn,RMS))
        else:
            out.append(None)   # Too little
    # end IF loop
    return out
    # end EVLASNAmpStats

def EVLAClipSNAmp(uv, SNver, arange, err, \
                  FGver=-1, logfile='', check=False, debug=False):
    """
    Flag SN table entries with amplitudes outside of [range[0]-range[1]]

    Optionally adds entry to flag (FG) table
    Returns with err set on error

    * uv         = UV data object
    * SNver      = SN table to flag
    * arange     = [min amp, max amp] allowed. list per IF
                   IF with None entry are ignored
    * err        = Python Obit Error/message stack
    * FGver      = FG table to add flags to, <=0 ->none
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    fblank = FArray.PGetBlank() # Magic blanking value
    # Number of IFs
    nif   = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocif"]]
    # Number of Stokes
    npoln = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocs"]]
    SNTab = uv.NewTable(Table.READONLY, "AIPS SN", SNver, err, \
                        numIF=nif, numPol=npoln)
    if err.isErr:
        return
    # Open
    SNTab.Open(Table.READWRITE, err)
    if err.isErr:
        return
    # Number of rows
    nrow =  SNTab.Desc.Dict["nrow"]
    count = 0; total = 0
    for i in range (0,nrow):    # Loop over rows
        SNrow = SNTab.ReadRow(i+1, err)
        if err.isErr:
            return
        dirty = False
        # Loop over IF
        for iif in range (0, nif):
            if arange[iif]!=None:
                amin = arange[iif][0]
                amax = arange[iif][1]
                if (SNrow["WEIGHT 1"][iif]>0.0) and (SNrow["REAL1"][iif]!=fblank):
                    total += 1
                    amp = (SNrow["REAL1"][iif]**2+SNrow["IMAG1"][iif]**2)**0.5
                    if (amp<amin) or (amp>amax):
                        # Flag table?
                        EVLAFlagSNClip(uv, SNrow, iif+1, 1, err, FGver=FGver, \
                                       logfile=logfile, check=check, debug=debug)
                        SNrow["REAL1"][iif]    = fblank
                        SNrow["IMAG1"][iif]    = fblank
                        SNrow["WEIGHT 1"][iif] = 0.0
                        count += 1
                        dirty = True
                # Second Poln
                if (npoln>1) and (SNrow["WEIGHT 2"][iif]>0.0) and (SNrow["REAL2"][iif]!=fblank):
                    total += 1
                    amp = (SNrow["REAL2"][iif]**2+SNrow["IMAG2"][iif]**2)**0.5
                    if (amp<amin) or (amp>amax):
                        # Flag table?
                        EVLAFlagSNClip(uv, SNrow, iif+1, 2, err, FGver=FGver, \
                                       logfile=logfile, check=check, debug=debug)
                        SNrow["REAL2"][iif]    = fblank
                        SNrow["IMAG2"][iif]    = fblank
                        SNrow["WEIGHT 2"][iif] = 0.0
                        count += 1
                        dirty = True
       # Rewrite if modified
        if dirty and not check:
            SNTab.WriteRow(i+1, SNrow, err)
            if err.isErr:
                return
  # end loop over rows

    # Close table
    SNTab.Close(err)
    if err.isErr:
        return

    mess = "Flagged %d of total %d Gain entries" % (count, total)
    printMess(mess, logfile)
    # end EVLAClipSNAmp

def EVLAFlagSNClip(uv, SNrow, IFno, poln, err, \
               FGver=-1, reason="BadAmp", logfile='', check=False, debug=False):
    """
    Write flag table entry for SN table row

    Returns with err set on error

    * uv         = UV data object
    * SNrow      = SN table row
    * IFno       = IF number to flag
    * poln       = polarization (1 or 2)
    * err        = Python Obit Error/message stack
    * FGver      = FG table to add flags to, <=0 ->none
    * reason     = reason string
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug
    """
    ################################################################
    if FGver<=0:   # Anthing wanted?
        return
    tr   = [SNrow["TIME"][0]-SNrow["TIME INTERVAL"][0],SNrow["TIME"][0]+SNrow["TIME INTERVAL"][0]]
    Ants = [SNrow["ANTENNA NO."][0],0]
    IFs  = [IFno, IFno]
    sid = SNrow["SOURCE ID"][0]
    if poln==1:
        Stokes="1011"
        amp = (SNrow["REAL1"][IFno-1]**2+SNrow["IMAG1"][IFno-1]**2)**0.5
    else:
        Stokes="0111"
        amp = (SNrow["REAL2"][IFno-1]**2+SNrow["IMAG2"][IFno-1]**2)**0.5
    if not check:
        UV.PFlag(uv, err, flagVer=FGver,
                 timeRange=tr, Ants=Ants, IFs=IFs, Stokes=Stokes,
                 Reason=reason)
    if err.isErr:
        return
    if debug:
        mess = "Flag SID %d Ant %d IF %d Poln %d Timerange %s - %s amp %f" % \
               (sid, Ants[0],IFno,poln,day2dhms(tr[0]),day2dhms(tr[1]), amp)
        printMess(mess, logfile)
# end EVLAFlagSNClip

def EVLACalModel(Source,
                 CalDataType="  ", CalFile=" ", CalName=" ", CalClass=" ", CalSeq=0, CalDisk=0, \
                 CalNfield=0, CalCCVer=1, CalBComp=[1], CalEComp=[0], CalCmethod="DFT", CalCmode="L1", CalFlux=0.0, \
                 CalModelFlux=0.0, CalModelSI=0.0,CalModelPos=[0.,0.], CalModelParm=[0.,0.,0.]):
    """
    Create a calibrator model

    returns dictionary with entries:
    * Source      = Calibrator source name
    * CalDataType = Calibrator model file data type (AIPS,FITS)
    * CalFile     = Calibrator model FITS input image if Type=='FITS'
    * CalName     = Calibrator model Cleaned AIPS  map name
    * CalClass    = Calibrator model Cleaned AIPS  map class
    * CalSeq      = Calibrator model Cleaned AIPS  map seq
    * CalDisk     = Calibrator model Cleaned AIPS  map disk
    * CalNfield   = Calibrator model No. maps to use for model
    * CalCCVer    = Calibrator model CC file version
    * CalBComp    = Calibrator model First CLEAN comp to use, 1/field
    * CalEComp    = Calibrator model Last CLEAN comp to use, 0=>all
    * CalCmethod  = Calibrator model Modeling method, 'DFT','GRID','    '
    * CalCmodel   = Calibrator model Model type: 'COMP','IMAG'
    * CalFlux     = Calibrator model Lowest CC component used
    * CalModelSI  = Calibrator Spectral index
    * CalModelFlux= Parameterized model flux density (Jy)
    * CalModelPos = Parameterized model Model position offset (asec)
    * CalModelParm= Parameterized model Model parameters (maj, min, pa, type)
    """
    out = {
        "Source":Source,
        "CalDataType":CalDataType,
        "CalFile":CalFile,
        "CalName":CalName,
        "CalClass":CalClass,
        "CalSeq":CalSeq,
        "CalDisk":CalDisk,
        "CalNfield":CalNfield,
        "CalCCVer":CalCCVer,
        "CalBComp":CalBComp,
        "CalEComp":CalEComp,
        "CalCmethod":CalCmethod,
        "CalCmodel":CalCmode,
        "CalFlux":CalFlux,
        "CalModelSI":CalModelSI,
        "CalModelFlux":CalModelFlux,
        "CalModelPos":CalModelPos,
        "CalModelParm":CalModelParm
        }
    return out
# end EVLACalModel

def EVLAStdModel(Cals, freq):
    """
    Check for standard models in a calibrator list
    """
    # Standard models in FITS files
    stdModel = []
    # 3C286Chi
    model = {"Source":["3C286","J1331+3030","1331+305=3C286"],
             "freqRange":[2.0e9,12.0e9],
             "file":"3C286ChiModel.fits","disk":1}
    stdModel.append(model)

    # loop testing
    for Cal in Cals:
        for model in stdModel:
            if (Cal["Source"] in model["Source"]) and \
            (freq>=model["freqRange"][0]) and \
            (freq<=model["freqRange"][1]):
                Cal["CalFile"] = model["file"]
                Cal["CalDisk"] = model["disk"]
                break
# end EVLAStdModel

def EVLAGetRefAnt(uv, Cals, err, solInt=10.0/60.0, flagVer=2,  nThreads=1, \
                  noScrat=[], logfile='', check=False, debug=False):
    """
    Find the best reference antenna

    Runs Calib on Cals using the center half of each spectrum and
    determine antenna with best average SNR
    Return reference antenna number

    * uv       = UV data object to calibrate
    * Cals     = List of calibrators possibly with model
    * err      = Obit error/message stack
    * solInt   = solution interval (min)
    * flagVer  = Input Flagging table version
    * nThreads = Number of threads to use
    * check    = Only check script, don't execute tasks
    * debug    = Run tasks debug, show input
    * noScrat  = list of disks to avoid for scratch files
    * logfile  = Log file for tasks
    """
    # Calib on Amp cals
    calib = ObitTask.ObitTask("Calib")
    try:
        calib.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    calib.taskLog  = logfile
    if not check:
        setname(uv,calib)
    calib.flagVer  = flagVer
    calib.solMode  = "P!A"
    calib.solType  = "L1"
    calib.nThreads = nThreads
    calib.solInt   = solInt
    calib.noScrat  = noScrat
    # Central half of channels
    # Channel selection
    if not check:
        d     = uv.Desc.Dict
        nchan = d["inaxes"][d["jlocf"]]
    else:
        nchan = 1
    # Number to drop off each end
    mchan = max (1, int(nchan/4))
    calib.BChan  = mchan
    calib.EChan  = nchan - mchan
    OK      = False   # Must have some work
    # Loop over calibrators
    for Cal in Cals:
        calib.Sources[0]= Cal["Source"]
        calib.DataType2 = Cal["CalDataType"]
        calib.in2File   = Cal["CalFile"]
        calib.in2Name   = Cal["CalName"]
        calib.in2Class  = Cal["CalClass"]
        calib.in2Seq    = Cal["CalSeq"]
        calib.in2Disk   = Cal["CalDisk"]
        calib.nfield    = Cal["CalNfield"]
        calib.CCVer     = Cal["CalCCVer"]
        calib.BComp     = Cal["CalBComp"]
        calib.EComp     = Cal["CalEComp"]
        calib.Cmethod   = Cal["CalCmethod"]
        calib.Cmodel    = Cal["CalCmodel"]
        calib.Flux      = Cal["CalFlux"]
        #calib.Alpha     = Cal["CalModelSI"]
        calib.modelFlux = Cal["CalModelFlux"]
        calib.modelPos  = Cal["CalModelPos"]
        calib.modelParm = Cal["CalModelParm"]

        if debug:
            calib.i
            calib.debug = debug
        #calib.prtLv = 5
        # Trap failure
        try:
            if not check:
                calib.g
                pass
        except Exception as exception:
            print(exception)
            mess = "Calib Failed retCode= "+str(calib.retCode)+" Source "+calib.Sources[0]
            printMess(mess, logfile)
            #return 1  # allow some failures
        else:
            OK = True
        # end calibration loop

    # Something work?
    if not OK:
        printMess("All calibrators failed", logfile)
        return 1

    # Open and close image to sync with disk
    if not check:
        uv.Open(UV.READONLY, err)
        uv.Close(err)

    # Digest SN table
    if not check:
        hiSN = uv.GetHighVer("AIPS SN")
        mess = "Using SN table %d"%(hiSN)
        printMess(mess, logfile)
        stats = EVLASNStats(uv, hiSN, 1.0, err, logfile=logfile, check=check, debug=debug)
        if err.isErr:
            raise  RuntimeError("Error finding reference antenna")
        refAnt = stats["bestRef"]
        del stats
    else:
        refAnt = 0
    return  refAnt
    # end EVLAGetRefAnt

def EVLASNStats(uv, SNver, solInt, err, refAnts=[0], logfile='', check=False, debug=False):
    """
    Find good timerange/ reference antenna on the basis of an SN table

    Returns with err set on error
    Return dict::

        {"Source":source, "souID":souID, "timeRange":(tbeg,tend),
         "Fract":fract_OK, "SNR":avg_SNR,"bestRef":refAnt}

    If there is no SU table or source ID not in table, source name is blank

    * uv         = UV data object
    * SNver      = SN table to test
    * solInt     = statistics interval (min)
    * refAnts    = If values given, then list of acceptable ref. ants
    * err        = Python Obit Error/message stack
    * logfile    = logfile for messages
    * check      = Only check script
    * debug      = Only debug - no effect
    """
    ################################################################
    badDict = {"Source":"None", "souID":0,"timeRange":[0.0,1000.0], \
               "Fract":0.0, "SNR":0.0, "bestRef":-1}
    # Number of IFs
    nif   = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocif"]]
    # Number of Stokes
    npoln = uv.Desc.Dict["inaxes"][uv.Desc.Dict["jlocs"]]
    npoln = min(2, npoln)   # No more than 2
    SNtab = uv.NewTable(Table.READONLY, "AIPS SN", SNver, err, \
                        numIF=nif, numPol=npoln)
    if err.isErr:
        return badDict
    # Make sure sorted
    Table.PSort(SNtab, "TIME", False, err)
    if err.isErr:
        return badDict
    # Number of antennas
    nant = SNtab.Desc.List.Dict["NO_ANT"][2][0]
    # Open
    SNtab.Open(Table.READONLY, err)
    if err.isErr:
        return badDict
    # Number of rows
    nrow =  SNtab.Desc.Dict["nrow"]
    # Better be some
    if nrow<2:
        OErr.PLog(err, OErr.MildError, "Empty SN table %d"%(SNver))
        return badDict
    # Initialize
    solIntD = solInt/1440.
    # time0   = -1.0e20       # Beginning time of current interval
    timeE   = -1.0e20       # End time of current interval
    tlast   = -1.0e20       # Last time
    # souId   = -10           # Current source ID
    accum   = []            # solution period statistics array
    times   = None
    SNR1    = None
    SNR2    = None
    CNT1    = None
    CNT2    = None
    antCnt  = None
    fract   = 0.0
    avgSNR  = 0.0

    totAnt  = []  # Total valid IF/poln count per antenna
    snrAnt  = []  # Total valid IF/poln SNR per antenna
    for i in range(0,nant):
        totAnt.append(0)
        snrAnt.append(0.0)

    # For each interval collect an accum entry containing
    # 0) source ID
    # 1) (beginning_time, end_time)
    # 2) Fraction of total ant/IF/poln occuring
    # 3) Average SNR
    # 4) [antenna_occurance_count]
    # 5) [[avg_SNR_per_ant/IF]]  Poln 1
    # 6) [[avg_SNR_per_ant/IF]]  Poln 2
    for i in range (0,nrow):    # Loop over rows
        SNrow = SNtab.ReadRow(i+1, err)
        if err.isErr:
            return
        time     = SNrow["TIME"][0]
        if i == 0:
            souID = SNrow["SOURCE ID"][0]
        curSouID = SNrow["SOURCE ID"][0]
        # New interval?
        if (time>timeE) or (souID!=curSouID):
            # Save any current values to accum
            if times:
                times[1] = tlast    # actual end time
                # Normalize accumulations by counts, overall statistics
                acnt   = 0
                sum    = 0.0
                fract  = 0.0
                avgSNR = 0.0
                for i in range(0,nant):
                    for j in range(0,nif):
                        if CNT1[i][j]>0:
                            totAnt[i]  += CNT1[i][j]
                            snrAnt[i]  += SNR1[i][j]
                            SNR1[i][j] /= CNT1[i][j]
                            acnt += 1
                            sum  += SNR1[i][j]
                        if (npoln>1) and  CNT2[i][j]>0:
                            snrAnt[i]  += SNR2[i][j]
                            totAnt[i]  += CNT2[i][j]
                            SNR2[i][j] /= CNT2[i][j]
                            acnt += 1
                            sum  += SNR1[i][j]
                if acnt>0:
                    avgSNR = sum / acnt
                fract = float(acnt) / float(nant*nif*npoln)
                pastSI = [souID, times, fract, avgSNR, antCnt, SNR1, SNR2]
                accum.append(pastSI)
            # Build new accumulators
            times = [time,time+solIntD]
            antCnt = []            # Occurences of this antenna
            SNR1   = []            # Antenna array of sums of poln1
            CNT1   = []            # Antenna array of counts of poln1
            for i in range(0,nant):
                antCnt.append(0)
                # per antenna
                snr1 = []
                cnt1 = []
                for j in range(0,nif):
                    snr1.append(0.0)
                    cnt1.append(0)
                SNR1.append(snr1)
                CNT1.append(cnt1)
            # Second poln?
            if npoln>1:
                SNR2 = []          # Antenna array of sums of poln2
                CNT2 = []          # Antenna array of sums of poln2
                for i in range(0,nant):
                    snr2 = []
                    cnt2 = []
                    for j in range(0,nif):
                        snr2.append(0.0)
                        cnt2.append(0)
                    SNR2.append(snr2)
                    CNT2.append(cnt2)
            # end build accumulators
        timeE = time + solIntD
        souID = curSouID
        tlast = time
        # end new period

        # Accumulate
        tlast = time  # Save last time
        iant = SNrow["ANTENNA NO."][0] - 1   # 0-rel antenna no.
        antCnt[iant] += 1
        # Loop over IF
        for iif in range (0, nif):
            if SNrow["WEIGHT 1"][iif]>0.0:
                SNR1[iant][iif] += SNrow["WEIGHT 1"][iif];
                CNT1[iant][iif] += 1;
            # Second Poln
            if npoln>1:
                if SNrow["WEIGHT 1"][iif]>0.0:
                    SNR2[iant][iif] += SNrow["WEIGHT 2"][iif];
                    CNT2[iant][iif] += 1;

    # end loop over rows

    # Final accumulation?
    times[1] = tlast    # actual end time
    # Normalize accumulations by counts, overall statistics
    acnt   = 0
    sum    = 0.0
    fract  = 0.0
    avgSNR = 0.0
    for i in range(0,nant):
        for j in range(0,nif):
            if CNT1[i][j]>0:
                totAnt[i]  += CNT1[i][j]
                snrAnt[i]  += SNR1[i][j]
                SNR1[i][j] /= CNT1[i][j]
                acnt += 1
                sum  += SNR1[i][j]
            if (npoln>1) and  CNT2[i][j]>0:
                snrAnt[i]  += SNR2[i][j]
                totAnt[i]  += CNT2[i][j]
                SNR2[i][j] /= CNT2[i][j]
                acnt += 1
                sum  += SNR1[i][j]
        if acnt>0:
            avgSNR = sum / acnt
        fract = float(acnt) / float(nant*nif*npoln)
        pastSI = [souID, times, fract, avgSNR, antCnt, SNR1, SNR2]
        accum.append(pastSI)
        # end loop

    # Close table
    SNtab.Close(err)
    if err.isErr:
        return badDict

    # Find highest fraction
    hiFract = 0.0
    for s in accum:
        hiFract = max (hiFract, s[2])

    # eliminate (negate avg SNR) entries with lower fract
    for s in accum:
        if s[2]<0.99*hiFract:
            s[3] = -s[3]

    # Find highest avg SNR
    hiSNR = 0.0
    hi = [0.0, [0.0,1000.0],  0.0, 0.0]
    for s in accum:
        if s[3]>hiSNR:
            hiSNR = s[3]
            hi = s

    # Normalize antenna average SNRs
    for i in range (0,nant):
        if totAnt[i]>0:
            snrAnt[i] /= totAnt[i]

    # deselect antennas not in refAnts (if any non zero)
    if refAnts[0]>0:
        for i in range (0,nant):
            drop = True
            for ra in refAnts:
                if ra==i+1:
                    drop = False
            # found it?
            if drop:
                snrAnt[i] = 0.0
                totAnt[i] = 0

    # Find best refant count - one with most valid occurences
    bestCnt = 0
    for i in range (0,nant):
        if totAnt[i]>bestCnt:
            bestCnt = totAnt[i]

    # Find antenna with count equal to bestCnt with highest SNR
    bestRef = 0
    hiSNR = 0.0
    for i in range (0,nant):
        if (totAnt[i]>=bestCnt) and (snrAnt[i]>hiSNR):
            bestRef = i+1
            hiSNR   = snrAnt[i]

    # Lookup source name if SU table present
    hiSU = uv.GetHighVer("AIPS SU")
    souName = "            "    # default
    if hiSU>= 1:
        SUtab = uv.NewTable(Table.READONLY, "AIPS SU", 1, err, \
                        numIF=nif,)
        SUtab.Open(Table.READONLY, err)
        if err.isErr:
            return  badDict
        # Number of rows
        nrow =  SUtab.Desc.Dict["nrow"]
        for i in range (0,nrow):    # Loop over rows
            SUrow = SUtab.ReadRow(i+1, err)
            if err.isErr:
                return  badDict
            curSouID = SUrow["ID. NO."][0]
            if hi!=None and curSouID==hi[0]:   # This it?
                souName = SUrow["SOURCE"][0]
                break;
        SUtab.Close(err)
        if err.isErr:
            return badDict

    if debug:
        print(totAnt,"\n", snrAnt,"\n")
        for s in accum:
            print(s[0],s[1],s[2],s[3])

    # Create output structure
    out = {"Source":souName, "souID":hi[0],"timeRange":hi[1], "Fract":hi[2], "SNR":hi[3], "bestRef":bestRef}
    if debug:
        print("SN Info",out)
    return out
    # end EVLASNStats

def EVLASaveOutFiles( pickleFile='manifest.pickle' ):
    """
    Save pipeline output files Python object in a pickle file.

    * pickleFile = name of pickle file
    """
    EVLAAddOutFile( os.path.basename(pickleFile), 'project', 'Python object pickle file' )
    SaveObject( manifest, pickleFile, True)
# end EVLASaveOutFiles

def EVLAMakeManifest( manifest=manifest ):
    """
    Extract filenames from the manifest structure and return as a list.
    """
    # Build a list of all manifest
    srcFiles = [] # list of files to be copied
    for file in manifest['project']:
        srcFiles.append( file['name'] )
    srcKeys = list(manifest['source'].keys())
    for srcKey in srcKeys:
        for file in manifest['source'][ srcKey ]:
            srcFiles.append( file['name'] )
    return srcFiles

def EVLAValidManifest( manifest=manifest, logFile=None):
    """
    Compare manifest with files in the current directory. Report differences.

    Return True if manifest and CWD are equal.  False otherwise.

    * manifest = manifest data object
    """
    ofList = EVLAMakeManifest( manifest=manifest )
    cwdList = os.listdir( './' )

    # List of files in manifest but not in CWD
    notInCwd = [file for file in ofList if file not in cwdList]
    if notInCwd:
        mess = "ERROR manifest.pickle contains files not in current directory!"
        printMess(mess, logFile)
        mess = "ERROR List of missing files:\n" + pprint.pformat(notInCwd)
        printMess(mess, logFile)
    # List of files in CWD but not in manifest
    notInOf  = [file for file in cwdList if file not in ofList]
    if notInOf:
        mess = "ERROR Current directory contains files not in manifest.pickle!"
        printMess(mess, logFile)
        mess = "ERROR List of missing files:\n" + pprint.pformat(notInOf)
        printMess(mess, logFile)
    if notInCwd or notInOf:
        return False # differ
    else:
        return True  # equal
# end EVLAValidManifest

def EVLAMakeParmFile(subs, parmfile, template=None):
    """
    Generate a parameter file from a template and a list of substitutions

    * subs     = list of substitutions as tuple: ("@PARAMETER@", "valuestring")
    * parmfile = output parameter file
    * template = name of template parameter file; if none, use default
    """
    if not template:
        template = os.getenv('EVLAPIPE','..')+'/EVLAContTemplateParm.py'
        if not os.path.exists(template):
            template = os.environ['OBIT'] + '/share/scripts/EVLAContTemplateParm.py'
            if not os.path.exists(template):
                template = 'EVLAContTemplateParm.py'
    fdin  = open(template, "r")
    fdout = open(parmfile,"w")
    line = fdin.readline()
    while (line):
        for s in subs:
            line = line.replace(s[0],s[1])
        fdout.write(line)
        line = fdin.readline()
    fdin.close()
    fdout.close()
# end EVLAMakeParmFile

def EVLAGetParms( fileDict):
    """
    Return a list for initializing the EVLA pipeline parameters file.

    The list contains 2-element sequence types (tuples).  The tuples contain
    a substitution key and a replacement string.

    * fileDict = a single file dictionary returned in the response from
      ParseASDM
    """
    # session = EVLAGetSessionCode( fileDict )
    # wavelength = 2.99e8/fileDict['VLAFreq']
    parms = [ ('@PROJECT@',    fileDict['project_code']),
              ('@SESSION@',    fileDict['session']),
              ('@BAND@',       fileDict['band']),
              ('@VLAFREQ@',    str(fileDict['VLAFreq'])),
              ('@VLACFG@',     str(fileDict['VLACfg'])),
              ('@SPANBW@',     str(fileDict['SpanBW'])),
              ('@DATAROOT@',   fileDict['DataRoot']),
              ('@CONFIG@',     str(fileDict['selConfig'])),
              ('@SELCHAN@',    str(fileDict['selChan'])),
              ('@BPCAL@',      str(fileDict['BPCal'])),
              ('@PHSCAL@',     str(fileDict['PhsCal'])),
              ('@AMPCAL@',     str(fileDict['AmpCal'])),
              ('@DLYCAL@',     str(fileDict['DlyCal'])),
              ('@PINCAL@',     str(fileDict['PCInsCals'])),
              ('@PRLDCAL@',    str(fileDict['RLDCal'])),
              ('@REFANT@',     str(fileDict['refAnt'])),
              ('@PLOTSRC@',    "'"+str(fileDict['PlotSrc'])+"'"),
              ('@PLOTTIME@',   str(fileDict['PlotTime'])),
              ('@TARGET@',     str(fileDict['Targets'])),
              #('@DESTDIR@',    fileDict['DestDir']),
              #('@ARCHFILEID@', fileDict['arch_file_id'])
              ]
    return parms
# EVLAGetParms

def EVLAGetSessionCode( fileDict ):
    """
    Get the project session code from a fileDict returned by
    PipeUtil.ParseASDM.

    * fileDict = dictionary returned by ParseASDM
    """
    # Get session from archive file name
    session = 'XX'
    #VLBA pattern = re.compile(r'EVLA_[A-Za-z]+[0-9]+([A-Za-z]+)')
    #VLBA  match = re.match( pattern, fileDict['logical_file'] )
    #VLBA if match:
    #VLBA     session = match.group(1)
    return session
# end EVLAGetSessionCode

def EVLAGetBandLetter( freq ):
    """
    Return the project observing band letter from frequency

    * freq  = Frequency in Hz
    """
    if freq<100.0e6:
        return "4"
    elif freq<900.0e6:
        return "P"
    elif freq<2.0e9:
        return "L"
    elif freq<3.7e9:
        return "S"
    elif freq<7.5e9:
        return "C"
    elif freq<12.0e9:
        return "X"
    elif freq<18.0e9:
        return "Ku"
    elif freq<26.5e9:
        return "K"
    elif freq<40.0e9:
        return "Ka"
    elif freq<50.0e9:
        return "Q"
    elif freq<117.0e9:
        return "A3"
    elif freq<163.0e9:
        return "A4"
    elif freq<211.0e9:
        return "A5"
    elif freq<275.0e9:
        return "A6"
    elif freq<375.0e9:
        return "A7"
    elif freq<510.0e9:
        return "A8"
    elif freq<730.0e9:
        return "A9"
    elif freq<960.0e9:
        return "A10"
    if freq<2000.0e9:
        return "A11"
    else:
        return "UK"
# end EVLAGetBandLetter

def EVLAGetRLDCal(asdm, config):
    """
    Return list of R-L phase and delay calibrator info of known calibrators
    [str((source_name, R-L phase, RM))]

    * asdm  = ASDM object
    * cid   = configuration ID
    """
    nope  =  [(None, None, None)]   # Default output
    callist = []
    # Known calibrators
    known = [ \
        {"name":"3C286", "pos2000":(3.5392577776, 0.53248521090), "tol":(0.001, 0.001), \
         "RLPhase":66.0, "RM":0.0}, \
        ]
    # Look through sources in ASDM field list
    field = asdm.Field
    scan  = asdm.Scan
    main  = asdm.Main
    for s in field:
        # Check known list
        for k in known:
            if abs(s["referenceDir"][0]-k["pos2000"][0])<k["tol"][0] and \
               abs(s["referenceDir"][1]-k["pos2000"][1])<k["tol"][1]:
                # was this observed in config
                OK = False
                for m in main:
                    if m["configDescriptionId"]==config:
                        for scn in scan:
                            if scn["sourceName"]==s["fieldName"]:
                                OK = True
                                break;
                    if OK:
                        break
                # If OK use whole thing as string
                if OK:  # Use it?
                    callist.append((s["fieldName"], k["RLPhase"], k["RM"]))
        return callist
    else:
        return nope
    # end EVLAGetRLDCal

def EVLAGetBandWavelength( fileDict ):
    """
    Return the representative wavelength for the EVLA receiver associated with
    the given file dictionary *fileDict*.

    * fileDict = archive file dictionary
    """
    wavelength = '??cm'
    # Define lists for band code, upper and lower band frequency, and wavelength
    ## BandCode= [    'P',    'P',    'L',    'S',   'C',   'X',   'U',   'K',   'Q',   'W']
    ## FreqLow = [   .312,   .596,   1.35,   2.15,  4.61,   8.0,  12.0,  21.7,  41.0,  80.0] # GHz
    ## FreqHi  = [   .342,   .626,   1.75,   2.35,  5.11,   8.8,  15.4,  24.1,  45.0,  90.0] # GHz
    ## WaveLen = [ '90cm', '50cm', '20cm', '13cm', '6cm', '3cm', '2cm', '1cm', '7mm', '3mm']
    # Combine P-band wavelengths
    BandCode= [       'P',    'L',    'S',   'C',   'X',   'U',   'K',   'Q',   'W']
    FreqLow = [      .312,   1.35,   2.15,  4.61,   8.0,  12.0,  21.7,  41.0,  80.0] # GHz
    FreqHi  = [      .626,   1.75,   2.35,  5.11,   8.8,  15.4,  24.1,  45.0,  90.0] # GHz
    WaveLen = [ '50-90cm', '20cm', '13cm', '6cm', '3cm', '2cm', '1cm', '7mm', '3mm']
    # For FITSAIPS files, get frequency from filename, convert to
    # representative wavelength
    if fileDict['format'] == 'FITSAIPS':
        pattern = re.compile('.*_(\d+\.\d+)([MG]HZ)')
        match = re.match( pattern, fileDict['logical_file'] )
        fGHz = 0.0
        if match:
            fGHz, unit = match.group( 1, 2 )
            fGHz = float( fGHz )
            if unit == 'MHZ':
                fGHz = fGHz / 1000
        for i,w in enumerate(WaveLen):
            if (fGHz >= FreqLow[i] and fGHz <= FreqHi[i]):
                wavelength = w
    # For all other files, or when frequency is not found in filename,
    # convert archive band letter to wavelength.
    if fileDict['format'] == 'FITS-IDI' or wavelength == '??cm':
        bandLetter = fileDict['obs_bands']
        wavelength = WaveLen[ BandCode.index( bandLetter ) ]
    return wavelength
# end EVLAGetBandWavelength

def EVLAParseASDM(ASDMRoot, err):
    """
    Parse an ASDM and set up for processing

    Return list of dicts per AIPS dataset:
    VLSFreq, VLAcfg, selConfig, selChan, BPCal, AmpCal, PhsCal, DlyCal
    * ASDMRoot = root of ASDM directory
    * err      = Obit error message object
    """
    out = []
    asdm = OASDM.OASDM(err, name="ASDM", DataRoot=ASDMRoot)
    configs = asdm.GetConfigs()

    VLACfg = asdm.GetArrayConfig()
    refAnt = 0  # Let script figure it out

    # Loop over configurations:
    for c in configs:
        cid     = c["configDescriptionId"]
        BPCal   = asdm.GetBandpassCal(cid)
        AmpCal  = asdm.GetAmpCal(cid)
        PhsCal  = asdm.GetPhaseCal(cid)
        DlyCal  = asdm.GetPhaseCal(cid)+asdm.GetAmpCal(cid)+asdm.GetBandpassCal(cid)
        Targets = asdm.GetTargets(cid)
        band    = EVLAGetBandLetter(c["avgRefFreq"])
        RLDCal  = EVLAGetRLDCal(asdm, cid)
        # Loop over no channels
        for n in c["nchands"]:
            plt  = asdm.Get1stBandpassScan(cid)
            dict = {
                "DataRoot":ASDMRoot,
                "VLAFreq":c["avgRefFreq"],
                "SpanBW":c["SpanBandwidth"],
                "VLACfg":VLACfg,
                "selConfig":cid,
                "selChan":n,
                "band":band,
                "BPCal":BPCal,
                "AmpCal":AmpCal,
                "PhsCal":PhsCal,
                "DlyCal":DlyCal,
                "Targets":Targets,
                "PlotSrc":plt['source'],
                "PlotTime":plt['timeRange'],
                "refAnt":refAnt,
                "PCInsCals":DlyCal,
                "RLPCal":"None",
                "rlrefAnt":refAnt,
                "RLDCal":RLDCal
                }
            out.append(dict)
    # End loops
    del asdm
    return out
# end EVLAParseASDM

#VLBA def EVLAPrepare( starttime, stoptime, fitsDest, outputDest, project=None,
#VLBA    template="EVLAContTemplateParm.py", parmFile=None ):
def EVLAPrepare( ASDMRoot, err, \
                 project=None, session=None, template=None, parmFile=None,
                 outputDest=''):
    """
    Prepare pipeline for processing.
    Create parameter file. Give user the command to execute the pipeline.

    * ASDMRoot = root directory of ASDM/BDF
    * err      = Obit message/error stack
    * project  = name of project, default = root of ASDMRoot
    * session  = session name of project, default = 'C'config'N'nchan
    * template = name of template parameter file, def "EVLAContTemplateParm.py"
    * parmFile = name of output parameter file; None => used default name
    """
    # Check that DataRoot exists
    if not os.path.exists(ASDMRoot):
        OErr.PLog(err, OErr.Fatal, ASDMRoot+" Does not exist")
        OErr.printErr(err)
        return
    # Get project name from ASDMRoot if not given
    if not project:
        parts   = ASDMRoot.split(os.sep)
        project = parts[len(parts)-1].split('.')[0]
    print("Project", project)
    #VLBA response = QueryArchive( starttime, stoptime, project )
    # Get config info and parameters
    fileList = EVLAParseASDM( ASDMRoot, err )
    #VLBA print SummarizeArchiveResponse( fileList )
    #VLBA print "Download file #: ",
    #VLBA fileNum = int( sys.stdin.readline() )
    # Loop over files
    print("Start pipeline with command(s):")
    for fileNum in range (0,len(fileList)):
        fileDict = fileList[fileNum]
        # ***** MORE WORK HERE
        fileDict['project_code'] = project
        if session:
            fileDict['session'] = session
        else:
            fileDict['session']      = 'C' + str(fileDict['selConfig']) + 'N' + str(fileDict['selChan'])
        #response = DownloadArchiveFile( fileDict, fitsDest )
        #VLBA if response != None:
        #VLBA     PollDownloadStatus( fileDict, fitsDest )
        parmList = EVLAGetParms( fileDict)
        #??? if not parmFile:
        parmFile = "EVLAContParm_" + fileDict['project_code'] + \
                   '_Cfg' + str(fileDict['selConfig']) + '_Nch' + str(fileDict['selChan']) + '.py'
        EVLAMakeParmFile( parmList, parmFile, template=template )
        print("ObitTalk EVLAContPipe.py AIPSSetup.py " + parmFile)
# end EVLAPrepare

def EVLAWriteVOTable( projMeta, srcMeta, filename="votable.xml", logfile='' ):
    """
    Write metadata and file information to a VOTable.

    * projMetadata = dictionary of project metadata
    * srcMetadata  = dictionary of single-source metadata
    """
    # now = datetime.datetime.utcnow()

    doc = xml.dom.minidom.Document()
    vo = doc.createElement("votable") # root element VOTABLE
    # # Specify IVOA VOTable Schema
    # vo.setAttribute("xmlns","http://www.ivoa.net")
    # vo.setAttribute("xmlns:xsi","http://www.w3.org/2001/XMLSchema-instance")
    # vo.setAttribute("xsi:schemaLocation",
    #     "http://www.ivoa.net http://www.ivoa.net/internal/IVOA/IvoaVOTable/VOTable-1.2-20090929")
    doc.appendChild(vo)

    rs2 = doc.createElement("resource") # RESOURCE Project Data
    rs2.setAttribute("name","Project Data")
    vo.appendChild(rs2)

    # Write project metadata
    keys = list(projMeta.keys())
    setAttribs = XMLSetAttributes # use short name - save space
    for key in keys:
        pr = doc.createElement("param")
        if key == "project":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype", "char"),
                              ("arraysize","*"),
                              ("ucd","meta.code") ] )
            XMLAddDescription( pr, "Project code" )
        elif key == "session":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","*"),
                              ("ucd","meta.code") ] )
            XMLAddDescription( pr, "Project session identifier" )
        elif key == "band":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","*"),
                              ("ucd","instr.bandpass;em.wl") ] )
            XMLAddDescription( pr, "Representative receiver wavelength" )
        elif key == "obsDate":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","10"),
                              ("ucd","time.start") ] )
            XMLAddDescription( pr, "Observing date" )
        elif key == "obsStart":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","float"),
                              ("ucd","time.start"),
                              ("unit","MJD") ] )
            XMLAddDescription( pr, "Observation start time (MJD)" )
        elif key == "obsStop":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","float"),
                              ("ucd","time.end"),
                              ("unit","MJD") ] )
            XMLAddDescription( pr, "Observation stop time (MJD)" )
        elif key == "procDate":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","10"),
                              ("ucd","time.processing") ] )
            XMLAddDescription( pr, "Pipeline processing date" )
        elif key == "PhsCals":
            # All strings in array must have same length
            maxLen = 0
            for s in projMeta[key]:
                length = len(s)
                if length > maxLen:
                    maxLen = length
            value = ""
            for s in projMeta[key]:
                # Concatenate strings, left justified, with min length maxLen+1
                value += "%-*s" % ( maxLen+1, s )
            arraysize = str(maxLen+1) + "x" + str( len(projMeta) )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","char"),
                              ("arraysize", arraysize ),
                              ("ucd","meta.id;src.calib") ] )
            XMLAddDescription( pr, "List of phase calibrators" )
        elif key == "AmpCals":
            # All strings in array must have same length
            maxLen = 0
            for s in projMeta[key]:
                length = len(s)
                if length > maxLen:
                    maxLen = length
            value = ""
            for s in projMeta[key]:
                # Concatenate strings, left justified, with min length maxLen+1
                value += "%-*s" % ( maxLen+1, s )
            arraysize = str(maxLen+1) + "x" + str( len(projMeta) )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","char"),
                              ("arraysize", arraysize ),
                              ("ucd","meta.id;src.calib") ] )
            XMLAddDescription( pr, "List of amp calibrators" )
        elif key == "BPCals":
            # All strings in array must have same length
            maxLen = 0
            for s in projMeta[key]:
                length = len(s)
                if length > maxLen:
                    maxLen = length
            value = ""
            for s in projMeta[key]:
                # Concatenate strings, left justified, with min length maxLen+1
                value += "%-*s" % ( maxLen+1, s )
            arraysize = str(maxLen+1) + "x" + str( len(projMeta) )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","char"),
                              ("arraysize", arraysize ),
                              ("ucd","meta.id;src.calib") ] )
            XMLAddDescription( pr, "List of bandpass calibrators" )
        elif key == "DlyCals":
            # All strings in array must have same length
            maxLen = 0
            for s in projMeta[key]:
                length = len(s)
                if length > maxLen:
                    maxLen = length
            value = ""
            for s in projMeta[key]:
                # Concatenate strings, left justified, with min length maxLen+1
                value += "%-*s" % ( maxLen+1, s )
            arraysize = str(maxLen+1) + "x" + str( len(projMeta) )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","char"),
                              ("arraysize", arraysize ),
                              ("ucd","meta.id;src.calib") ] )
            XMLAddDescription( pr, "List of delay calibrators" )
        elif key == "anNames":
            numAnt = len( projMeta[key] )
            value=""
            for name in projMeta[key]:
                value += name + " " # 2-char name plus space => len = 3
            arraysize = "3x" + str( numAnt )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","char"),
                              ("arraysize", arraysize),
                              ("ucd","meta.code") ] )
            XMLAddDescription( pr, "List of antennas used in observation (antenna code)" )
        elif key == "freqCov":
            pairList = projMeta[key]
            arraysize = "2x" + str( len( pairList ) )
            value = ""
            for pair in pairList:
                value += "%f %f " % ( pair[0], pair[1] )
            setAttribs( pr, [ ("name", key ),
                              ("value", value ),
                              ("datatype","double"),
                              ("arraysize", arraysize),
                              ("ucd","em.freq"),
                              ("unit", "Hz") ] )
            XMLAddDescription( pr, "Observational frequency coverage: list of lower- and upper-side band pairs" )
        elif key == "minFringe":
            setAttribs( pr, [ ("name", key ),
                              ("value", str( projMeta[key] ) ),
                              ("datatype","double"),
                              ("ucd","phys.angSize"),
                              ("unit", "asec") ] )
            XMLAddDescription( pr, "Minimum fringe spacing (arcseconds)" )
        elif key == "dataSet":
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","*"),
                              ("ucd","meta.dataset;meta.file") ] )
            XMLAddDescription( pr, "Name of archived raw-data file" )
        elif key in ("obitVer", "aipsVer", "pyVer", "sysInfo", "pipeVer"):
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char"),
                              ("arraysize","*"),
                              ("ucd","meta.version;meta.software") ] )
            XMLAddDescription( pr, "Version string" )
        elif key in ("archFileID"):
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","int" ),
                              ("ucd","meta.record;meta.dataset" ) ] )
            XMLAddDescription( pr,
                "Archive file ID (integer unique to each archive file)" )
        elif key in ("fileSetID"):
            setAttribs( pr, [ ("name", key ),
                              ("value", projMeta[key] ),
                              ("datatype","char" ),
                              ("arraysize","*"),
                              ("ucd","meta.record;meta.dataset" ) ] )
            XMLAddDescription( pr,
                "Pipeline data product set identification string (project code + observing date + archive file ID)" )
        else:
            mess = "WARN - Project report key/value " + key + "/" + str(projMeta[key]) + \
                " not written to VOTable"
            printMess(mess, logfile)
            continue # skip append and go to next key

        rs2.appendChild(pr)

    table_ProjFiles = doc.createElement("table")
    table_ProjFiles.setAttribute("name","files")
    rs2.appendChild(table_ProjFiles)

    fi = doc.createElement("field")
    fi.setAttribute("name","file name")
    fi.setAttribute("datatype","char")
    fi.setAttribute("arraysize","*")
    fi.setAttribute("ucd","meta;meta.file")
    table_ProjFiles.appendChild(fi)

    fi = fi.cloneNode( False )
    fi.setAttribute("name","description")
    fi.setAttribute("ucd","meta.title")
    table_ProjFiles.appendChild(fi)

    dt = doc.createElement("data")
    table_ProjFiles.appendChild(dt)

    td = doc.createElement("tabledata")
    dt.appendChild(td)

    # Make copy of node for later use
    table_SrcFiles = table_ProjFiles.cloneNode( True )

    # Project files
    EVLAWriteVOTableFiles( manifest['project'], td)

    # Loop over all sources
    for src in srcMeta:
        rs3 = doc.createElement("resource") # RESOURCE (each source)
        rs3.setAttribute("name", src["Source"] )
        vo.appendChild(rs3)

        # Src metadata
        keys = list(src.keys())
        for key in keys:
            pr = doc.createElement("param")
            if key == "ObsDate":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","char"),
                                  ("arraysize","10"),
                                  ("ucd","time.start") ] )
                XMLAddDescription( pr, "Observing date" )
            elif key == "Source":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","char"),
                                  ("arraysize","*"),
                                  ("ucd","meta.code") ] )
                XMLAddDescription( pr, "Source name" )
            elif key == "RA":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.eq.ra;src"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Right ascension (phase center)" )
            elif key == "Dec":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.eq.dec;src"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Declination (phase center)" )
            elif key == "Exposure":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","time.duration;obs.exposure"),
                                  ("unit","8.64x10+4s") ] ) # frac of day
                XMLAddDescription( pr, "Exposure time (fraction of day)" )
            elif key == "numVis":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","int"),
                                  ("ucd","meta.number;obs") ] )
                XMLAddDescription( pr, "Number of visibility measurements" )
            elif key == "RAPnt":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.eq.ra;instr"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Right ascension (telescope pointing)" )
            elif key == "DecPnt":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.eq.dec;instr"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Declination (telescope pointing)" )
            elif key == "Freq":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","em.freq"),
                                  ("unit","Hz") ] )
                XMLAddDescription( pr, "Center frequency" )
            elif key == "BW":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","instr.bandwidth"),
                                  ("unit","Hz") ] )
                XMLAddDescription( pr, "Bandwidth" )
            elif key == "Size":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.angDistance"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Image angular size" )
            elif key == "Cells":
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","pos.angResolution"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Cell angular size (resolution)" )
            elif key.find("Peak") == 1:
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","phot.flux.density;stat.max"),
                                  ("unit","Jy") ] )
                XMLAddDescription( pr, "Peak flux" )
            elif key.find("Sum") == 1:
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","phot.flux.density;arith"),
                                  ("unit","Jy") ] )
                XMLAddDescription( pr, "Sum of clean component flux" )
            elif key.find("RMS") == 1:
                setAttribs( pr, [ ("name", key ),
                                  ("value", src[key] ),
                                  ("datatype","double"),
                                  ("ucd","stat.stdev;phot.flux.density"),
                                  ("unit","Jy") ] )
                XMLAddDescription( pr, "Root-mean-square flux" )
            elif key.find("Beam") == 1:
                value = ""
                for float in src[key]:
                    value += str( float ) + " "
                setAttribs( pr, [ ("name", key ),
                                  ("value", value ),
                                  ("datatype","double"),
                                  ("arraysize","3"),
                                  ("ucd","instr.beam"),
                                  ("unit","deg") ] )
                XMLAddDescription( pr, "Elliptical synthesized beam shape (major axis, minor axis, rotation)" )
            else:
                mess = "WARN - Source (" + src['Source'] + ") report key/value " + key + \
                    "/" + str(src[key]) + " not written to VOTable"
                printMess(mess, logfile)
                continue # skip append and go to next key
            rs3.appendChild(pr)

        tb = table_SrcFiles.cloneNode( True ) # make deep copy for this source
        rs3.appendChild(tb)
        nodeList = tb.getElementsByTagName('tabledata')
        td = nodeList.item(0)
        # if this source is in the manifest single-source dictionary...
        if src['Source'] in manifest['source']:
            fileList = manifest['source'][ src['Source'] ]
            EVLAWriteVOTableFiles( fileList, td )

    votable = open( filename, "w" )
    doc.writexml( votable, addindent="  ", newl="\n") # readable format
    # doc.writexml( votable ) # production format
# end EVLAWriteVOTable

def EVLAWriteVOTableFiles( fileList, tableData ):
    """
    Write output file data to a VOTable.

    * fileList = List of file dictionaries, from manifest
    * tableData = TABLEDATA element to which child elements will be appended
    """
    doc = xml.dom.minidom.Document()
    for file in fileList:
        tr = doc.createElement("tr")
        tableData.appendChild(tr)

        td = doc.createElement("td")
        tr.appendChild(td)
        tx = doc.createTextNode( file['name'] )
        td.appendChild(tx)

        td = doc.createElement("td")
        tr.appendChild(td)
        tx = doc.createTextNode( file['description'] )
        td.appendChild(tx)
# end EVLAWriteVOTableFiles(

def EVLAAddOutFile( filename, target, description, logFile=""):
    """
    Add file names and descriptions to the manifest object. Verify that the
    file is not already in manifest before adding.

    * filename = name of file to be added
    * target = name of target source; or 'project' if this is a multi-source file
    * description = description of file
    """
    filen = os.path.basename(filename)
    mess = "INFO Adding " + filen + \
           " (for " + target + ") to list of output files."
    printMess(mess, logFile)
    d = { 'name' : filen, 'description' : description }
    projFiles = manifest['project']
    srcFiles = manifest['source']

    if ( target == 'project' ): # If this is a project file
        if ( not d in projFiles ): # If file is not already in list
            projFiles.append( d ) # Add file to project list
    else: # else, it is a single-source file
        if target in srcFiles: # If files already exist for this source
            if ( not d in srcFiles[ target ] ): # If file is not already in list
                srcFiles[ target ].append( d ) # Add file to target list
        else:
            # No files yet present for this source.
            # Create a new dictionary key and assign it a list w/ member d
            srcFiles[ target ] = [ d ]
    # End EVLAAddOutFile

def EVLAFetchOutFiles( pickleFile='manifest.pickle', logFile=None):
    """
    Fetch a pickled python object that holds pipeline output files. Check that
    each output file still exists.  If it does not, remove it from the object,
    and print a warning.

    * pickleFile = pickle file to be fetched
    """
    if not os.path.exists( pickleFile ):
        return
    global manifest
    manifest = FetchObject( pickleFile )
    exists = [ file for file in manifest['project']
        if os.path.exists( file['name'] ) ]
    notExists = [ file for file in manifest['project']
        if not os.path.exists( file['name'] ) ]
    for file in notExists:
        print("Doesn't exist (project) " + file['name'])
        mess = "WARN Pipeline manifest pickle points to non-existant project file: " \
               + file['name'] + "\n  Removing file from manifest."
        printMess(mess, logFile)
    manifest['project'] = exists

    # Check single-source files
    srcFiles = manifest['source']
    srcFiles_copy = copy.deepcopy( srcFiles )
    srcKeys = list(srcFiles.keys())
    for srcName in srcKeys:
        # Check files for each source
        for file in srcFiles_copy[ srcName ]:
            if not os.path.exists( file['name'] ):
                srcFiles[ srcName ].remove( file ) # remove from original
                print("Doesn't exist (source) " + file['name'])
                mess = "WARN Pipeline manifest pickle points to non-existant source file: " \
                       + file['name'] + "\n  Removing file from manifest."
                printMess(mess, logFile)
        # If this source no longer has files, remove it
        if len( srcFiles[ srcName ] ) == 0:
            del srcFiles[ srcName ]
# end EVLAFetchOutFiles

def EVLAAIPSName( project):
    """
    Derive AIPS Name.  AIPS file name will be project+session with project
    truncated to fit in 12 characters.

    * project = project name
    * session = session code
    """
    ################################################################
    Aname = Aname=(project.strip())[0:12]
    return Aname
    # end EVLAAIPSName

def EVLAKntrPlots( err, catNos=[], imClass='?Clean', imName=[], project='tProj',
    session='tSes', band='tB', disk=1, cleanUp=True, logfile='', check=False,
    debug=False ):
    """
    Create contour plots for the specified images. Image selection is made
    based on the input catalog numbers (catNos), or, if catalog numbers are not
    given, based on a pattern match to the image name and class. Pattern
    matching follows the rules of function AMcat(). One PS file is generated
    for each unique image name. Multiple images with the same name will be added
    to the same file on different pages. Arugments project, session, and band
    are used only in creating file names.

    * err = Python Obit Error/message stack
    * catNos = catalog numbers of images
    * imClass = class of images to plot (used only if catNos is empty)
    * imName = name of images to plot; None = make plots for each source (used
      only if catNos is empty)
    * project = project name
    * session = project session
    * band = project receiver band code
    * disk = data disk number
    * logfile = file for log messages
    * debug = Turn on debug mode
    """
    # Setup AIPS task KNTR
    kntr = AIPSTask.AIPSTask("kntr")
    try:
        kntr.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    kntr.msgkill = 5
    kntr.dogrey  = 0
    kntr.dovect  = 0
    kntr.ltype   = -5 # Show border and labels w/o creation date and PL version
    kntr.cbplot  = -18 # half-power beam in bottom right; no contour overlay
    # Set contour levels in units of cntr.clev (defined below). Contours begin
    #   with -2, -2^0.5, 2^0.5, and then increase as powers of root two.
    levs = [ -2, -2**(0.5), 2**(0.5) ]
    for i in range(27):
        l = levs[-1] * 2.0**( 0.5 )
        levs = levs + [ l ]
    kntr.levs = AIPSTask.AIPSList( levs )

    # Instantiate AIPS task LWPLA
    lwpla = AIPSTask.AIPSTask("lwpla")
    try:
        lwpla.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    lwpla.msgkill = 5

    # If catalog numbers not given, get all images matching class imClass
    # and with names in list imName.
    if (not catNos):
        if not imName:
            imName = '*'
        elif not type(imName) == list:
            imName = [ imName ]
        for n in imName:
            catNos += AMcat(disk=disk, Aname=n, Aclass=imClass, giveList=True )
    for cno in catNos: # loop over images
        image = getname(cno)
        mess = "INFO Creating contour plot for image " \
        + string.strip(image.Aname) + ' . ' + string.strip(image.Aclass)
        printMess(mess, logfile)

        # Run KNTR to make plot
        setname(image, kntr)
        # Contour level unit = 2 * RMS noise
        stats = imstat(image, err)
        kntr.clev = 2 * stats['RMSHist']
        # Set the size of the contour plot: use the inner quarter
        d = image.Desc.Dict
        nx = d['inaxes'][0]
        ny = d['inaxes'][1]
        kntr.trc[1]=3*nx/4.0; kntr.trc[2]=3*ny/4.0;
        kntr.blc[1]=nx/4.0;   kntr.blc[2]=ny/4.0;
        name = image.Aname.rstrip() # Image name w/o whitespace
        outfile = project+'_'+name+'.cntr.ps'
        # Trap failure - KNTR too stupid to live
        try:
            if not check:
                kntr.g
        except Exception as exception:
            print(exception)
            mess = "Kntr Failed - continuing anyway"
            printMess(mess, logfile)
        else:
            # Run LWPLA to make PS file
            setname(image, lwpla)
            lwpla.outfile = './'+outfile # output to current directory
            # Trap failure
            try:
                if not check:
                    lwpla.g
            except Exception as exception:
                print(exception)
                mess = "Lwpla Failed - continuing anyway"
                printMess(mess, logfile)
            else:
                pass
        if os.path.exists(outfile):    # May not exist
            EVLAAddOutFile( outfile, name, "Contour plot" )

        # Convert 1st page of PS (Stokes I) to JPG
        tmpPS, tmpPDF, jpg = ['%s.%s' % (os.path.splitext(outfile)[0], file_ext) for file_ext in ['ps', 'pdf', 'jpg']]
        printMess('Converting '+outfile+' (1st page) -> '+jpg,logfile)
        # Extract first page of PS; Convert to PDF; Convert to JPG
        # (on 64-bit, converting directly from PS to JPG does not work)
        cmd = 'pstops 1000:0 ' + outfile + ' > ' + tmpPS + ';' + \
            'ps2pdf ' + tmpPS + ' ' + tmpPDF + ';' + \
            'convert -density 96 ' + tmpPDF + ' ' + jpg
        rtn = os.system(cmd)
        if rtn == 0:
            EVLAAddOutFile( jpg, name, "Contour plot (Stokes I)" )
            if cleanUp:
                os.remove(tmpPS)
                os.remove(tmpPDF)
        else:
            # Print error message and leave the PS file
            mess="Error occurred while converting PS to JPG"
            printMess(mess,logfile)

        # Delete plot files
        if not check:
            image.ZapTable("AIPS PL", -1,err)
# end EVLAKntrPlots

def EVLADiagPlots( uv, err, cleanUp=True, JPEG=True, sources=None, project='',
    session='', band='', logfile=None, check=False, debug=False ):
    """
    Generate single source diagnostic plots.

    This method uses the averaged, calibrated data generated by the
    pipeline to produced single source diagnostics. The diagnostics
    can be used to assess the quality of the visibility data underlying
    the pipeline image maps and to assess the quality of the pipeline
    algorithms.

    * uv = UV data object to plot
    * err = Python Obit Error/message stack
    * cleanUp = clean up temporary files when finished
    * JPEG = if True, make JPEG plots; else make PS
    * sources = list of sources; None = make plots for each source
    * logfile =  logfile for messages
    * check = Only check script
    * debug = Turn on debug mode
    """

    mess = "Generating diagnostic plots for each source"
    printMess(mess, logfile)

    avgClass = 'UVAvgT' # uv average temporary data
    avgSeq = 1

    # Average data over: 10 sec, all IFs, all channels
    calAvgTime = 1 # temporal averaging (sec)
    printMess("Averaging: "+str(calAvgTime)+" sec interval, all IFs, all channels",
        logfile = logfile)
    rtn = KATCalAvg( uv, avgClass=avgClass, avgSeq=avgSeq, err = err,
        logfile = logfile, check=check, debug = debug, CalAvgTime = calAvgTime,
        avgFreq = 3, # avg all IFs
        chAvg   = 1, # avg all channels (should already have been done)
        doCalib = 2, # apply calibration
        doBand  = 0, # do not calibrate bandpass; already calibrated
        flagVer = 1  # Apply any flags
        )
    if rtn != 0:
        mess = "Error averaging data. KATCalAvg returned: " + str(rtn)
        printMess(mess, logfile)
        return rtn

    # Get the newly averaged data set: most recent file with class UVAvg
    uvAvg = None
    if not check:
        uvname = uv.GetName()+"_Cal"
        uvAvg = UV.newPAUV(uvname, uv.Aname, avgClass, uv.Disk, avgSeq,
            True, err)

    # Put source list into slist
    if not sources:
        slist = EVLAAllSource(uvAvg,err,logfile=logfile,check=check,debug=debug)
    else:
        slist = sources
    if not type(slist) == list:
        slist = [slist]

    # Setup UVPLT
    uvplt = AIPSTask.AIPSTask("uvplt")
    try:
        uvplt.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    if not check:
        setname(uvAvg, uvplt)
    uvplt.stokes  = 'I' # unpolarized
    uvplt.ltype   = -3  # Omit PL number and creation time
    uvplt.msgkill = 5   # Omit babble
    printMess("Plotting stokes "+uvplt.stokes, logfile=logfile)

    # Setup LWPLA
    lwpla = AIPSTask.AIPSTask("lwpla")
    try:
        lwpla.userno = OSystem.PGetAIPSuser()   # This sometimes gets lost
    except Exception as exception:
        pass
    lwpla.msgkill = 5
    if not check:
        setname(uvAvg, lwpla)

    # Define plots: file => filename string, bparm => UVPLT
    plotTypes =  ( { 'file' : 'amp', 'bparm' : [3,1]   , 'desc': 'Amp vs. uv Dist'},
                   { 'file' : 'uv' , 'bparm' : [6,7,2],  'desc': 'v vs. u '},
                   { 'file' : 'ri' , 'bparm' : [9,10],   'desc': 'Im vs. Re'} )

    # Loop over sources
    for (i,s) in enumerate(slist):
        mess = "INFO Generating diagnostic plots for source "+s+ \
        " ("+str(i+1)+"/"+str(len(slist))+")"
        printMess(mess, logfile)
        uvplt.sources[1] = s
        # Loop over plot types
        for plot in plotTypes:
            uvplt.bparm   = AIPSTask.AIPSList( plot['bparm'] )
            uvplt.msgkill = 5   # Omit babble

            # Create output file name
            outfile = project+'_'+s+'.'+plot['file']+'.ps'
            lwpla.outfile = outfile # output to output directory

            # Remove preexisting file
            if os.path.exists(outfile): os.remove(outfile)

            if not check:
                try:
                    uvplt.go()
                    lwpla.go()
                except Exception as exception:
                    mess = "ERROR Plotting failed - continuing anyway"
                    printMess(mess, logfile)
                    mess = "ERROR "+ str(exception)
                    printMess(mess, logfile)
                else:
                    if JPEG:
                        # Convert PS -> PDF; Convert PDF -> JPG
                        # (on 64-bit, converting directoy PS -> JPG fails)
                        tmpPDF, jpg = ['%s.%s' % (os.path.splitext(outfile)[0], file_ext) for file_ext in ['pdf', 'jpg']]
                        printMess('Converting '+outfile+' -> '+jpg,logfile)
                        cmd = 'convert ' + outfile + ' ' + tmpPDF + ';' + \
                            'convert -density 96 ' + tmpPDF + ' ' + jpg
                        rtn = os.system(cmd)
                        if rtn == 0 and os.path.exists(jpg):
                            EVLAAddOutFile( jpg, s, plot['desc'] )
                            if cleanUp:
                                os.remove(outfile) # Remove the PS file
                                os.remove(tmpPDF)
                        else:
                            # Print error message and leave the PS file
                            mess="Error occurred while converting PS to JPG"
                            printMess(mess,logfile)

     # Open/close UV to update header
    if not check:
        uvAvg.Open(UV.READONLY,err)
        uvAvg.Close(err)
    if err.isErr:
        OErr.printErr(err)
        mess = "Update UV header failed"
        printMess(mess, logfile)
        return 1
    if cleanUp:
        printMess('Cleaning up temporary data',logfile)
        if not check:
            zap(uvAvg)

    # end EVLADiagPlot

def KATProjMetadata( uv, AIPS_VERSION, err,
    PCals=[], ACals=[], BPCals=[], DCals=[],
    project='project', session='session', band='band', dataInUVF='',
    archFileID='' ):
    """
    Return a dictionary holding project metadata. Contents:

    ===============  ========================================================
    "project"        observation project name
    "session"        observation project session
    "CorrMode"       correlator code
    "obsDate"        observation date
    "obsStart"       observation start time (MJD)
    "obsStop"        observation stop time (MJD)
    "procDate"       pipeline processing date
    "PhsCals"        array of phase calibrators
    "AmpCals"        array of amplitude calibrators
    "BPCals"         array of bandpass calibrators
    "DlyCals"        array of delay calibrators
    "obitVer"        Obit version (TBD)
    "aipsVer"        AIPS version
    "pyVer"          Python version
    "sysInfo"        system information on processing machine (uname -a)
    "anNames"        names of all antennas used
    "freqCov"        frequency coverage (low & up sideband pairs for all IFs)
    "minFring"       minimum fringe spacing (asec)
    "dataSet"        Data set archive file name
    "archFileID"     Archive file ID
    ===============  ========================================================

    * uv = uv data object for which the report will be generated
    * AIPS_VERSION = AIPS version information
    * err = Python Obit Error/message stack
    * PCals  = list of phase cal models
    * ACals  = list of amp cal models
    * BPCals = list of bandpass cal models
    * DCals  = list of delay cal models
    * project = Observation project name
    * session = Observation project session
    * band = correlator mode code
    * dataInUVF = data set archive file name
    * archFileID = archive file ID
    """
    # Get lists of calibrator names from model lists.
    PCalList = []
    for s in PCals:
        PCalList.append(s['Source'])
    ACalList = []
    for s in ACals:
        ACalList.append(s['Source'])
    BPCalList = []
    for s in BPCals:
        BPCalList.append(s['Source'])
    DCalList = []
    for s in DCals:
        DCalList.append(s['Source'])
    r = {}
    r["project"] = project
    r["session"] = session
    r["CorrMode"] = band # Correlator mode
    r["obsDate"] = uv.Desc.Dict["obsdat"] # observation date
    times = getStartStopTime( uv, err )
    r["obsStart"] = times[0]
    r["obsStop"] = times[1]
    r["procDate"] = str( datetime.date.today() ) # processing date
    r["obitVer"] = Version() # Obit version
    r["pipeVer"] = getSVNVersion(os.getenv("EVLAPIPE",".")) # Pipeline version
    # Does this need to be passed as a function argument?
    r["aipsVer"] = AIPS_VERSION + '(' + str( datetime.date.today() ) + ')' # AIPS version
    r["pyVer"] = sys.version # python version
    p = os.popen("uname -a") # get sys info
    r["sysInfo"] = p.read()
    r["PhsCals"] = PCalList # list of phase calibrators
    r["AmpCals"] = ACalList # list of amp calibrators
    r["BPCals"]  = BPCalList # list of bandpass calibrators
    r["DlyCals"] = DCalList # list of delay calibrators
    parts = dataInUVF.split(os.sep)
    r["dataSet"] = parts[len(parts)-1]
    r["archFileID"] = archFileID # archive file ID
    r["fileSetID"] = r["project"] + "_" + r["obsDate"][2:].replace('-','') + "_" + \
        str(r["archFileID"])

    # Get antenna names and positions
    antab = uv.NewTable(Table.READONLY,"AIPS AN",1,err)
    antab.Open(Table.READONLY,err)
    OErr.printErrMsg(err) # catch table open errors
    nrow = antab.Desc.Dict["nrow"]
    annames = []
    anpos = []
    for i in range(1,nrow+1):
        anrow = antab.ReadRow(i, err)
        name = anrow["ANNAME"][0].rstrip()
        annames.append( name )
        pos = anrow["STABXYZ"]
        anpos.append( pos )
    antab.Close(err)
    r["anNames"] = annames # list of antennas used

    # Get the frequency coverage
    d = uv.Desc.Dict # UV data descriptor dictionary
    refFreq = d["crval"][ d["jlocf"] ] # reference frequency
    fqtab = uv.NewTable(Table.READONLY,"AIPS FQ",1,err)
    fqtab.Open(Table.READONLY,err)
    OErr.printErrMsg(err) # catch table open errors
    nrow = fqtab.Desc.Dict["nrow"]
    freqCov = []
    for i in range(1,nrow+1):
        fqrow = fqtab.ReadRow(i, err)
        freq = fqrow["IF FREQ"]
        bw = fqrow["TOTAL BANDWIDTH"]
        sb = fqrow["SIDEBAND"] # +1 => 'IF FREQ' is upper-side band; -1 => lower-side band
        for i in range( len(freq) ):
            f1 = refFreq + freq[i] # 1st bound of IF
            f2 = f1 + sb[i] * bw[i] # 2nd bound of IF
            fc = [ f1, f2 ]
            fc.sort()
            freqCov.append( fc ) # sort bounds and add to list
    fqtab.Close(err)
    r["freqCov"] = freqCov

    # Calculate the minimum fringe spacing
    maxBl = 0 # maximum baseline length
    # maxBlAnt = [] # antenna indices forming maximum baseline
    for (i, p1) in enumerate( anpos ):
        for (j, p2) in enumerate( anpos ):
            if i == j: continue
            dpos = [0, 0, 0]
            for k in range(3):
                dpos[k] = p1[k] - p2[k]
            # Baseline length in meters
            bl = ( dpos[0]**2 + dpos[1]**2 + dpos[2]**2 )**(0.5)
            if bl > maxBl:
                maxBl = bl
                # maxBlAnt = [i, j]
    # r["maxBl"] = [ annames[ maxBlAnt[0] ], # antennas forming max baseline
    #                annames[ maxBlAnt[1] ] ]
    lightSpeed = 299792458 # ( meters / second)
    wavelength = lightSpeed / refFreq
    maxBlWavelength = maxBl / wavelength # max baseline (units of wavelength)
    # minimum fringe spacing (asec)
    r["minFringe"] = 1 / maxBlWavelength / 4.8481368e-6
    return r
# end EVLAProjMetadata

def EVLASrcMetadata(uv, err,  FreqID=1, Sources=None, \
                    seq=1, sclass="IClean", \
                    Stokes="I", logfile='', check=False, debug=False):
    """
    Generate report info for a list of targets in AIPS files

    Returns a report which is a list of dicts, each of which contains

    ===========  ==========================================
    "Source"     Source name
    "haveImage"  True if images were made,
    "ObsDate"    Observing date as "yyyy-mm-dd"
    "numVis"     Number of visibilities (ignoring flagging)
    "Exposure"   Total integration time (day)
    "RA"         Source RA (deg) at standard equinox
    "Dec"        Source Dec (deg) at standard equinox
    ===========  ==========================================

    following present if haveImage True

    ========  ==============================================
    "RAPnt"   Antenna pointing RA (deg) at standard equinox
    "DecPnt"  Antenna pointing Dec (deg) at standard equinox
    "Freq"    Reference frequency (Hz)
    "BW"      Image bandwidth (Hz)
    "Size"    Width of image in deg (From Stokes I)
    "Cells"   Cell spacing in deg (From Stokes I)
    "Stokes"  Stokes parameters of images
              for each s in Stokes:

              =======  ===============================
              "sSum"   Sum of clean components in Jy
              "sPeak"  Peak pixel brightness in Jy
              "sRMS"   RMS noise in inner quarter (Jy)
              "sBeam"  Beam (maj, min, PA) (deg)
              =======  ===============================

     following present if haveImage False
    ========  ==============================================
    ========  ==============================================

    * uv         = UV data object
    * err        = Python Obit Error/message stack
    * Sources    = Source name or list of names to use
      If an empty list all sources in uv are included
    * seq        = sequence number of images
    * sclass     = Image class, first character replaced with char in Stokes
    * FreqID     = Frequency group identifier
    * Stokes     = Stokes parameters of images
    * logfile    = logfile for messages
    * check      = Only check script, don't execute tasks
    * debug      = show input
    """
    ################################################################
    mess = "Generate source statistics "
    printMess(mess, logfile)

    # If list empty get all sources
    if type(Sources)==list:
        sl = Sources
    else:
        sl = [Sources]

    if len(sl)<=0:
        slist = EVLAAllSource(uv,err,logfile=logfile,check=check,debug=debug)
    else:
        slist = sl

    # Init output
    Report = []

    # Image disk assumed same as uv
    disk = uv.Disk
    user = OSystem.PGetAIPSuser()

    # Loop over slist
    for sou in slist:
        sdict = {"Source":sou, "haveImage":False}  # Init source structure
        sdict["ObsDate"]  = uv.Desc.Dict["obsdat"]
        # Observing stats
        obstat = EVLAGetTimes (uv, sou, err, logfile=logfile, check=check, debug=debug)
        sdict["numVis"]   = obstat["numVis"]
        sdict["Exposure"] = obstat["Exposure"]
        sdict["RA"]       = obstat["RA"]
        sdict["Dec"]      = obstat["Dec"]
        # Test if image exists
        cno = AIPSDir.PTestCNO(disk, user, sou, Stokes[0:1]+sclass[1:], "MA", seq, err)
        if cno <= 0 :
            Report.append(sdict)  # Save source info
            continue
        # Image statistics, loop over Stokes
        for s in Stokes:
            klass = s+sclass[1:]
            x = Image.newPAImage(s, sou, klass, disk, seq, True, err)
            hd = x.Desc.Dict
            sdict[s+"Beam"] = (hd["beamMaj"],hd["beamMin"],hd["beamPA"])
            # Some from Stokes I only
            if s == 'I':
                sdict["haveImage"] = True
                sdict["Size"]    = hd["inaxes"][1]*hd["cdelt"][1]
                sdict["Cells"]   = hd["cdelt"][1]
                sdict["RAPnt"]   = hd["obsra"]
                sdict["DecPnt"]  = hd["obsdec"]
                sdict["Freq"]    = hd["crval"][hd["jlocf"]]

                #sdict["BW"]      = np.abs(hd["cdelt"][hd["jlocf"]]) Remove this as it is meaningless for MF images
                sdict["Stokes"]  = Stokes
            blc = [hd["inaxes"][0]/4,hd["inaxes"][1]/4]
            trc = [3*hd["inaxes"][0]/4,3*hd["inaxes"][1]/4]
            stat = imstat(x,err,blc=blc,trc=trc)  # Image statistics inner quarter
            if abs(stat["Max"]) >  abs(stat["Min"]):
                sdict[s+"Peak"] = stat["Max"]
            else:
                sdict[s+"Peak"] = stat["Min"]
            sdict[s+"RMS"]  = stat["RMSHist"]
            print(x.GetHighVer("AIPS CC"))
            if x.GetHighVer("AIPS CC")>0:
                sdict[s+"Sum"]  = EVLAGetSumCC(x, err, logfile=logfile, check=check, debug=debug)
            else:
                sdict[s+"Sum"]  = -1.0
        # End stokes image loop
        Report.append(sdict)  # Save source info
    # end loop over sources

    # Give terse listing
    for sdict in Report:
        mess = "\n Source = "+sdict["Source"]+", Exposure="+"%5.3f"%(sdict["Exposure"]*24.)+" hr"
        printMess(mess, logfile)
        if sdict["haveImage"]:
            mess = "IPol Beam = ("+"%8.3f"%(sdict["IBeam"][0]*3600000.0)+", %8.3f"%(sdict["IBeam"][1]*3600000.0)+ \
                ", %6.1f"%(sdict["IBeam"][2])+") mas, mas, deg"
            printMess(mess, logfile)
            for s in Stokes:
                mess = "Stokes "+s+" Sum CC="+"%8.3f"%(sdict[s+"Sum"])+", Peak="+"%8.3f"%(sdict[s+"Peak"])+ \
                    ", RMS="+"%8.5f"%(sdict[s+"RMS"])+" Jy"
                printMess(mess, logfile)
    # End terse listing
    return Report
# end EVLASrcMetadata

def KATHTMLReport( projMetadata, srcMetadata, outfile="report.html",
    logFile="" ):
    """
    Write an HTML report on the processed data set.  This includes information
    on project (multi-source) metadata and data files as well as single source
    metadata and data files.

    * projMetadata = dictionary of project metadata
    * srcMetadata  = dictionary of single-source metadata
    * outfile = name of HTML output file
    * logFile = file for writing log messages
    """
    mess = "Writing HTML report to " + outfile
    printMess( mess, logFile )
    file = open( outfile, 'w' )
    EVLAAddOutFile( outfile, 'project', "HTML Report generated by pipeline" )
    s = """
<html><head><style>
table {
    border-collapse : collapse;
}
/* table,th,td {
    border : 1px solid grey;
} */
.plot {
    height: 200;
}
</style></head><body>"""
    file.write( s )

    s  = "<h2> Contents </h2>"
    s += "<a href='#project_Section'> Project </a>"
    for metadata in srcMetadata:
        # Create links to each section
        s += ' - <a href="#' + metadata['Source'] + '_Section">' + \
            metadata['Source'] + '</a>'
    file.write( s )

    # Write project metadata
    s  = "<a id='project_Section'><h2> Project </h2></a>\n"
    s += "<h3> Metadata </h3>\n"
    s += "<table>\n"
    # keys = [ 'project', 'session', 'band', 'obsDate', 'procDate', 'contCals',
    #          'goodCal', 'anNames', 'freqCov', 'minFringe', 'obitVer',
    #          'aipsVer', 'pyVer', 'sysInfo' ]
    keys = None
    s += writeTableRow( projMetadata, keys )
    s += "</table>\n"
    file.write( s )

    # Write project output files
    projFiles = manifest['project']
    s  = "<h3> Files </h3>\n"
    s += "<table>\n"
    for d in projFiles:
        s += '<tr><th><a href="' + d['name'] + '">' + d['name'] + '</a>' + \
             '</th><td>' + d['description'] + '</td></tr>\n'
    s += '</table>\n'
    s += '<hr>\n'
    file.write( s )

    # Write metadata and data files for each source
    for metadata in srcMetadata:
        # Create list of keys
        keys = [ 'ObsDate', 'RA', 'Dec', 'Exposure', 'numVis', 'haveImage' ]
        # if haveImage is True, these keys are also present
        iKeys = [ 'RAPnt', 'DecPnt', 'Freq', 'Size', 'Cells' ]
        # These are present for each Stokes, w/ the Stokes character prepended
        sKeys = [ 'Sum', 'Peak', 'RMS', 'Beam' ]
        if metadata['haveImage'] == True:
            keys = keys + iKeys
            for s in metadata['Stokes']:
                for k in sKeys:
                    keys.append(s + k)

        # Write metadata table
        s  = '<a id="' + metadata['Source'] + '_Section">' + \
             '<h2>' + metadata['Source'] + "</h2></a>\n"
        s += "<h3> Metadata </h3>\n"
        s += '<table>\n'
        s += writeTableRow( metadata, keys )
        s += '</table>\n'
        file.write(s)

        def writeImageCell( file ):
            str = '<td><a href="' + file['name'] + '"> <img src="' + \
                file['name'] + '" alt="' + file['description'] + \
                '" class="plot"/></a></td>\n'
            return str

        s  = "<table>\n"
        s += "<tr><th>Image</th><th>Amp vs Baseline</th><th>Im vs Re</th>"
        s += "<th>V vs U</th></tr>\n"
        s += "<tr>\n"
        if metadata['Source'] in manifest['source']:
            fileList = manifest['source'][ metadata['Source'] ]
            tList = list(range(4))
            for f in fileList:
                if f['name'].find('IClean.jpeg') != -1: tList[0] = f
                if f['name'].find('amp.jpg') != -1: tList[1] = f
                if f['name'].find('ri.jpg') != -1: tList[2] = f
                if f['name'].find('uv.jpg') != -1: tList[3] = f
            for f in tList:
                if type(f)==dict:
                    s += writeImageCell( f )
        s += '</tr></table>\n'
        file.write(s)

        # Write output file table
        s  = "<h3> Files </h3>\n"
        s += "<table>\n"
        if metadata['Source'] in manifest['source']:
            for d in manifest['source'][ metadata['Source'] ]:
                s += '<tr><th><a href="' + d['name'] + '">' + d['name'] + \
                     '</a>' + '</th><td>' + d['description'] + '</td></tr>'
        s += "</table>\n"
        s += "<hr>\n"
        file.write(s)

    s = "</body></html>"
    file.write(s)
    file.close()
# end EVLAHTMLReport

def writeTableRow( dict, keys=None ):
    """
    Write the contents of a dictionary as an HTML table.

    * dict = dictionary whose contents will be written
    * keys = dictionary keys to be written
    """
    if not keys:
        keys = list(dict.keys())
        keys.sort()
    s = ""
    # Write a row of the HTML table for every key in keys.  Handle some key
    # values specially.
    for key in keys:
        if key == "anNames":
            # Print the number of antennas when printing the list of ant names
            s += '<tr><th>' + key + '</th>' + \
                 '<td> Number = ' + str( len( dict[key] ) ) + ', ' + \
                 'Names = ' + str( dict[key] ) + \
                 '</td></tr>\n'
        elif key == 'freqCov':
            # Print frequencies with limited precision
            fs = ""
            for freqs in dict[key]:
                fs += '(%.3e, %.3e) ' % ( freqs[0], freqs[1] )
            s += '<tr><th>' + key + '</th><td>' + fs + '</td></tr>\n'
        elif (key == 'RA') or (key == 'RAPnt'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + UVDesc.PRA2HMS(dict[key]) + '</td></tr>\n'
        elif (key == 'Dec') or (key == 'DecPnt'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + UVDesc.PDec2DMS(dict[key]) + '</td></tr>\n'
        elif (key == 'timeRange'):
            s += '<tr><th> Time Range </th>' + \
                 '<td>' + day2dhms(dict['timeRange'][0]) + ' - ' + \
                  day2dhms(dict['timeRange'][1]) + ' </td></tr>\n'
        elif (key == 'Freq'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%6.3f"%(dict[key]*1.0e-9) + ' GHz </td></tr>\n'
        elif (key == 'BW'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%6.3f"%(dict[key]*1.0e-6) + ' MHz </td></tr>\n'
        elif (key == 'SNR'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%6.1f"%(dict[key]) + ' </td></tr>\n'
        elif (key == 'Exposure'):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%6.3f"%(dict[key]*24.0) + ' Hours </td></tr>\n'
        elif (key == 'Size') or (key == "Cells"):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%8.5f"%(dict[key]*3.6e3) + ' asec </td></tr>\n'
        elif (key == 'ISum') or (key == "QSum") or (key == "USum"):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%8.3f"%(dict[key]*1.0e3) + ' mJy </td></tr>\n'
        elif (key == 'IPeak') or (key == "QPeak") or (key == "UPeak"):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%8.3f"%(dict[key]*1.0e3) + ' mJy </td></tr>\n'
        elif (key == 'IRMS') or (key == "QRMS") or (key == "URMS"):
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + "%8.5f"%(dict[key]*1.0e3) + ' mJy </td></tr>\n'
        elif (key == 'IBeam'):
            s += '<tr><th> Clean Beam </th>' + \
                 '<td>' + \
            " %6.4f, %6.4f, %6.1f"%(dict[key][0]*3.6e3, dict[key][1]*3.6e3, dict[key][2]) + \
            ' (asec,asec,deg) </td></tr>\n'
        elif (key == 'FailProc'):
            s += '<tr><th> Failing process </th>' + \
                 '<td>' +  " %s"%(dict[key])+' </td></tr>\n'
        else:
            # Everything else
            s += '<tr><th>' + key + '</th>' + \
                 '<td>' + str( dict[key] ) + '</td></tr>\n'
    return s
# end writeTableRow


