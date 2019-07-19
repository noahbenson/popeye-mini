#! /usr/bin/python

# This script gets run whenever the user runs the docker with the argument "solve" or no argument.

import sys, os, six, json, warnings, pimms, multiprocessing as mp, numpy as np
import popeye, popeye.og_hrf as og_hrf
import neuropythy as ny

def warn(arg):
    warnings.warn(arg)
    sys.stderr.write(arg + '\n')
    sys.stderr.flush()
def note(arg):
    sys.stdout.write(arg + '\n')
    sys.stdout.flush()

def _dofit(args):
    import popeye
    (FitClass, model, data, grids, bounds, ijk, grid_n, autofit, verbose) = args
    return FitClass(model, data, grids, bounds, Ns=grid_n)

def solver(params):
    '''
    solver(params) accepts a parameter dictionary params and solves the pRF models implied by them.
    
    The return value of solver is a dictionary of pRF parameters or statistics; e.g., a dictionary
    might contain keys 'r2', 'sigma', 'x', and 'y'.
    '''
    tr = params['TR_length']
    # go ahead and make the stimulus:
    stimulus_array = params['stimulus']
    stimulus_array = np.round(stimulus_array/np.max(stimulus_array)).astype('short')
    # figure out screen width from assumed distance of 50 and d2p:
    stimpx  = np.min(stimulus_array.shape[:2])
    stimdeg = stimpx / params['pixels_per_degree']
    stimcm  = 2 * 50 * np.tan(stimdeg/2 * np.pi/180)
    stimulus = popeye.visual_stimulus.VisualStimulus(stimulus_array, 50, stimcm, 0.5, tr, 'short')
    # A few other optional parameters:
    grid_n = params.get('grid_n', 5)
    minmax_x = params.get('range_x',     (-stimdeg, stimdeg))
    minmax_y = params.get('range_y',     (-stimdeg, stimdeg))
    minmax_s = params.get('range_sigma', (0.05, stimdeg * 0.75))
    minmax_h = params.get('range_hrf',   (-6, 6))
    grids = [minmax_x, minmax_y, minmax_s, minmax_h]
    # Get the data and mask ready...
    data = params['data']
    mask = params.get('mask', None)
    # okay, now go ahead and solve:
    hrf   = popeye.utilities.double_gamma_hrf
    model = og_hrf.GaussianModel(stimulus, hrf)
    model.hrf_delay = -0.25
    args = [(og_hrf.GaussianFit, model, data[i,j,k], grids, grids, (i,j,k), grid_n, True, False)
            for i in np.arange(data.shape[0])
            for j in np.arange(data.shape[1])
            for k in np.arange(data.shape[2])
            if (mask is None or mask[i,j,k])]
    pool = mp.Pool()
    fits = pool.map(_dofit, args)
    pool.close()
    pool.join()
    # okay, reconstruct these into results volumes
    res = {k:np.full(data.shape, np.nan)
           for k in ['x', 'y', 'sigma', 'baseline', 'gain', 'hrf_delay']}
    for (arg,fit) in zip(args, fits):
        ijk = arg[5]
        for (k,v) in zip(['x', 'y', 'sigma', 'baseline', 'gain', 'hrf_delay'],
                         [fit.x, fit.y, fit.sigma, fit.baseline, fit.beta, fit.hrf_delay]):
            res[k][ijk] = v
    return res
    
# The idea is that we process each subdirectory of the input dir as an experiment directory unless
# the input directory itself is an experiment directory:
if os.path.isfile('/input/params.json'): test_dirs = ['/input']
else: test_dirs = [fl for fl0 in os.listdir('/input') for fl in [os.path.join('/input', fl0)]
                   if os.path.isdir(fl) and os.path.isfile(os.path.join(fl, 'parmss.json'))]
# for each test dir, we need to load the params, the stimulus, and the data:
tests = []
for tdir in test_dirs:
    note('Examining %s...' % (tdir,))
    tt = {}
    # Load the params first:
    try:
        with open(os.path.join(tdir, 'params.json'), 'r') as fl:
            params = json.load(fl)
    except Exception:
        warn('Could not load params.json file in dir: %s' % (tdir,))
        continue
    # Then get the stimfile:
    stimfile = params.get('stimulus_file', 'stimulus.nii.gz')
    if not os.path.isabs(stimfile): stimfile = os.path.join(tdir, stimfile)
    if not os.path.isfile(stimfile):
        warn('Could not find designated stimfile (%s) in test dir %s!' % (stimfile, tdir))
        continue
    stim = ny.load(stimfile, to='image')
    # Then the data:
    datafile = params.get('data_file', 'data.nii.gz')
    if not os.path.isabs(datafile): datafile = os.path.join(tdir, datafile)
    if not os.path.isfile(datafile):
        warn('Could not find designated datafile (%s) in test dir %s!' % (datafile, tdir))
        continue
    data = ny.load(datafile, to='image')
    # Okay, make sure there is an indication of the screen width:
    if 'pixels_per_degree' not in params:
        if 'screen_width' in params and 'screen_distance' in params:
            sw = params['screen_width']
            sd = params['screen_distance']
            d2p = 2 * np.arctan2(sw/2, sd)
        else:
            warn('Could not deduce screen pixels per degree for test dir %s!' % (tdir,))
            continue
    else: d2p = params['pixels_per_degree']
    # Get the TR length and the frame rate
    trlen = params.get('TR_length', None)
    if trlen is None:
        trlen = data.header.get_zooms()[-1]
        truni = data.header.get_xyzt_units()[-1]
        trlen = pimms.mag(pimms.quant(trlen, 'sec' if truni is None else truni), 'second')
    frate = params.get('frame_rate', None)
    if frate is None:
        frate = stim.header.get_zooms()[-1]
        fruni = stim.header.get_xyzt_units()[-1]
        frate = pimms.mag(pimms.quant(frate, 'sec' if fruni is None else fruni), 'second')
    # see if there is a mask:
    mask = None
    if 'mask_file' in params:
        maskfile = params['mask_file']
        if not os.path.isabs(maskfile): maskfile = os.path.join(tdir, maskfile)
        if not os.path.isfile(stimfile):
            warn('Could not find mask file (%s) in test dir %s!' % (maskfile, tdir))
        else: mask = ny.load(maskfile, to='image')
    # Okay, now convert into something more standard:
    params['frame_rate'] = frate
    params['pixels_per_degree'] = d2p
    params['TR_length'] = trlen
    stim = np.asarray(stim.dataobj)
    params['stimulus'] = np.reshape(stim, [stim.shape[0],stim.shape[1],-1])
    params['data'] = np.asarray(data.dataobj)
    if mask is None: params['mask'] = np.ones(params['data'].shape[:-1], dtype='bool')
    else: params['mask'] = np.asarray(mask.dataobj)
    # Okay, now we can call the solver:
    note('   Solving...')
    try:
        results = solver(params)
        # Now, write out each of the results
        for (k,v) in six.iteritems(results):
            flnm = os.path.join(tdir, 'out_' + k + '.nii.gz')
            ny.save(flnm, v, 'nifti')
    except Exception:
        warn('Exception raised while solving test dir: %s' % (tdir,))
        raise

sys.exit(0)

