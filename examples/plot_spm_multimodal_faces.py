"""
Minimal script for preprocessing single-subject data (two session)

Author: DOHMATOB Elvis, Bertrand Thirion, 2015

Note: this example takes a lot of time because the input are lists of 3D images
sampled in different position (encoded by different) affine functions.
"""

print(__doc__)

# standard imports
import numpy as np
from scipy.io import loadmat
import pandas as pd

# imports for GLM business
from nilearn.image import concat_imgs, resample_img, mean_img
from nistats.design_matrix import make_design_matrix
from nistats.glm import FirstLevelGLM
from nistats.datasets import fetch_spm_multimodal_fmri

# fetch spm multimodal_faces data
subject_data = fetch_spm_multimodal_fmri()

# experimental paradigm meta-params
tr = 2.
drift_model = 'Cosine'
hrf_model = 'Canonical With Derivative'
period_cut = 128.

# resample the images
fmri_img = [concat_imgs(subject_data.func1, auto_resample=True),
            concat_imgs(subject_data.func2, auto_resample=True)]
affine, shape = fmri_img[0].get_affine(), fmri_img[0].shape
print('Resampling the second image (this takes time)...')
fmri_img[1] = resample_img(fmri_img[1], affine, shape[:3])
# Create mean image for display
mean_image = mean_img(fmri_img)

# make design matrices
design_matrices = []
for idx in range(2):
    # build paradigm
    n_scans = fmri_img[idx].shape[-1]
    timing = loadmat(getattr(subject_data, "trials_ses%i" % (idx + 1)),
                     squeeze_me=True, struct_as_record=False)

    faces_onsets = timing['onsets'][0].ravel()
    scrambled_onsets = timing['onsets'][1].ravel()
    onsets = np.hstack((faces_onsets, scrambled_onsets))
    onsets *= tr  # because onsets were reporting in 'scans' units
    conditions = (['faces'] * len(faces_onsets) +
                  ['scrambled'] * len(scrambled_onsets))
    paradigm = pd.DataFrame({'name': conditions, 'onset': onsets})

    # build design matrix
    frame_times = np.arange(n_scans) * tr
    design_matrix = make_design_matrix(
        frame_times, paradigm, hrf_model=hrf_model, drift_model=drift_model,
        period_cut=period_cut)
    design_matrices.append(design_matrix)

# specify contrasts
contrast_matrix = np.eye(design_matrix.shape[1])
contrasts = dict([(column, contrast_matrix[i])
                  for i, column in enumerate(design_matrix.columns)])
# more interesting contrasts
contrasts = {
    'faces-scrambled': contrasts['faces'] - contrasts['scrambled'],
    'scrambled-faces': -contrasts['faces'] + contrasts['scrambled'],
    'effects_of_interest': np.vstack((contrasts['faces'],
                                      contrasts['scrambled']))
    }

# fit GLM
print('Fitting a GLM')
fmri_glm = FirstLevelGLM(standardize=False).fit(fmri_img, design_matrices)

# compute contrast maps
print('Computing contrasts')
from nilearn import plotting

for contrast_id, contrast_val in contrasts.items():
    print("\tcontrast id: %s" % contrast_id)
    z_map, = fmri_glm.transform(
        [contrast_val] * 2, contrast_name=contrast_id, output_z=True)
    plotting.plot_stat_map(
        z_map, bg_img=mean_image, threshold=3.0, display_mode='z',
        cut_coords=3, black_bg=True, title=contrast_id)

plotting.show()
