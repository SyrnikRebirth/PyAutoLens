import os

import numpy as np
import shutil

from autofit import conf
from autofit.mapper import model_mapper as mm
from autofit.mapper import prior
from autofit.mapper import prior_model as pm
from autofit.optimize import non_linear as nl
from autolens.data import ccd
from autolens.data.array import grids
from autolens.data.array.util import array_util
from autolens.lens import ray_tracing
from autolens.model.galaxy import galaxy, galaxy_model as gm
from autolens.model.profiles import light_profiles as lp
from autolens.pipeline import phase as ph
from test.integration import integration_util

dirpath = os.path.dirname(os.path.realpath(__file__))
conf.instance = conf.Config("{}/config".format(dirpath),
                            "{}/output/".format(dirpath))

dirpath = os.path.dirname(dirpath)
output_path = '{}/output'.format(dirpath)

test_name = "test"


def simulate_integration_image(test_name, pixel_scale, lens_galaxies, source_galaxies, target_signal_to_noise):
    output_path = "{}/test_files/data/".format(os.path.dirname(os.path.realpath(__file__))) + test_name + '/'
    psf_shape = (11, 11)
    image_shape = (150, 150)

    psf = ccd.PSF.simulate_as_gaussian(shape=psf_shape, pixel_scale=pixel_scale, sigma=pixel_scale)

    grid_stack = grids.GridStack.grid_stack_for_simulation(shape=image_shape, pixel_scale=pixel_scale,
                                                           sub_grid_size=1, psf_shape=psf_shape)

    image_shape = grid_stack.regular.padded_shape

    if not source_galaxies:

        tracer = ray_tracing.TracerImagePlane(lens_galaxies=lens_galaxies, image_plane_grid_stack=grid_stack)

    elif source_galaxies:

        tracer = ray_tracing.TracerImageSourcePlanes(lens_galaxies=lens_galaxies, source_galaxies=source_galaxies,
                                                     image_plane_grid_stack=grid_stack)

    ### Setup as a simulated image_coords and output as a fits for an lensing ###

    ccd_simulated = ccd.CCDData.simulate_to_target_signal_to_noise(array=tracer.image_plane_image_for_simulation,
                                                                   pixel_scale=pixel_scale,
                                                                   target_signal_to_noise=target_signal_to_noise,
                                                                   exposure_time_map=np.ones(image_shape),
                                                                   background_sky_map=10.0 * np.ones(image_shape),
                                                                   psf=psf, seed=1)

    if os.path.exists(output_path) == False:
        os.makedirs(output_path)

    array_util.numpy_array_2d_to_fits(array_2d=ccd_simulated.image, file_path=output_path + '/image.fits',
                                      overwrite=True)
    array_util.numpy_array_2d_to_fits(array_2d=ccd_simulated.noise_map, file_path=output_path + '/noise_map.fits',
                                      overwrite=True)
    array_util.numpy_array_2d_to_fits(array_2d=psf, file_path=output_path + '/psf.fits', overwrite=True)
    array_util.numpy_array_2d_to_fits(array_2d=ccd_simulated.exposure_time_map,
                                      file_path=output_path + '/exposure_map.fits', overwrite=True)


class TestAdvancedModelMapper(object):
    def test_fully_qualified_paramnames(self):
        mapper = mm.ModelMapper()
        galaxy_model = gm.GalaxyModel(light_profile=lp.EllipticalLightProfile)
        light_profile = galaxy_model.light_profile
        mapper.galaxy_model = galaxy_model

        assert light_profile.name_for_prior(light_profile.axis_ratio) == "axis_ratio"
        assert light_profile.name_for_prior(light_profile.centre.centre_0) == "centre_0"

        assert galaxy_model.name_for_prior(light_profile.axis_ratio) == "light_profile_axis_ratio"

        assert mapper.param_names[0] == "galaxy_model_light_profile_centre_0"


class TestPhaseModelMapper(object):

    def test_pairing_works(self):

        test_name = 'pair_floats'

        integration_util.reset_paths(test_name, output_path)

        sersic = lp.EllipticalSersic(centre=(0.0, 0.0), axis_ratio=0.8, phi=90.0, intensity=1.0, effective_radius=1.3,
                                     sersic_index=3.0)

        lens_galaxy = galaxy.Galaxy(light_profile=sersic)

        simulate_integration_image(test_name=test_name, pixel_scale=0.5, lens_galaxies=[lens_galaxy],
                                   source_galaxies=[], target_signal_to_noise=10.0)

        path = "{}/".format(
            os.path.dirname(os.path.realpath(__file__)))  # Setup path so we can output the simulated image.

        ccd_data = ccd.load_ccd_data_from_fits(image_path=path + '/test_files/data/' + test_name + '/image.fits',
                                               psf_path=path + '/test_files/data/' + test_name + '/psf.fits',
                                               noise_map_path=path + '/test_files/data/' + test_name + '/noise_map.fits',
                                               pixel_scale=0.1)

        class MMPhase(ph.LensPlanePhase):

            def pass_priors(self, results):
                self.lens_galaxies.lens.sersic.intensity = self.lens_galaxies.lens.sersic.axis_ratio

        phase = MMPhase(lens_galaxies=dict(lens=gm.GalaxyModel(sersic=lp.EllipticalSersic)),
                        optimizer_class=nl.MultiNest, phase_name="{}/phase1".format(test_name))

        initial_total_priors = phase.variable.prior_count
        phase.make_analysis(data=ccd_data)

        assert phase.lens_galaxies[0].sersic.intensity == phase.lens_galaxies[0].sersic.axis_ratio
        assert initial_total_priors - 1 == phase.variable.prior_count
        assert len(phase.variable.flat_prior_model_tuples) == 1

        print(phase.variable.flat_prior_model_tuples)
        print(phase.variable.info)

        lines = list(
            filter(lambda line: "axis_ratio" in line or "intensity" in line, phase.variable.info.split("\n")))

        assert len(lines) == 2
        assert "lens_galaxies_lens_sersic_axis_ratio                                                  UniformPrior, lower_limit = 0.2, upper_limit = 1.0" in lines
        assert "lens_galaxies_lens_sersic_intensity                                                   UniformPrior, lower_limit = 0.2, upper_limit = 1.0" in lines

    if os.path.exists(output_path):
        shutil.rmtree(output_path)

    def test_constants_work(self):
        name = "const_float"
        test_name = '/const_float'

        integration_util.reset_paths(test_name, output_path)

        sersic = lp.EllipticalSersic(centre=(0.0, 0.0), axis_ratio=0.8, phi=90.0, intensity=1.0, effective_radius=1.3,
                                     sersic_index=3.0)

        lens_galaxy = galaxy.Galaxy(light_profile=sersic)

        simulate_integration_image(test_name=test_name, pixel_scale=0.5, lens_galaxies=[lens_galaxy],
                                   source_galaxies=[], target_signal_to_noise=10.0)
        path = "{}/".format(
            os.path.dirname(os.path.realpath(__file__)))  # Setup path so we can output the simulated image.

        ccd_data = ccd.load_ccd_data_from_fits(image_path=path + '/test_files/data/' + test_name + '/image.fits',
                                               psf_path=path + '/test_files/data/' + test_name + '/psf.fits',
                                               noise_map_path=path + '/test_files/data/' + test_name + '/noise_map.fits',
                                               pixel_scale=0.1)

        class MMPhase(ph.LensPlanePhase):

            def pass_priors(self, results):
                self.lens_galaxies.lens.sersic.axis_ratio = 0.2
                self.lens_galaxies.lens.sersic.phi = 90.0
                self.lens_galaxies.lens.sersic.intensity = 1.0
                self.lens_galaxies.lens.sersic.effective_radius = 1.3
                self.lens_galaxies.lens.sersic.sersic_index = 3.0

        phase = MMPhase(lens_galaxies=dict(lens=gm.GalaxyModel(sersic=lp.EllipticalSersic)),
                        optimizer_class=nl.MultiNest, phase_name="{}/phase1".format(name))

        phase.optimizer.n_live_points = 20
        phase.optimizer.sampling_efficiency = 0.8

        phase.make_analysis(data=ccd_data)

        sersic = phase.variable.lens_galaxies[0].sersic

        assert isinstance(sersic, pm.PriorModel)

        assert isinstance(sersic.axis_ratio, prior.Constant)
        assert isinstance(sersic.phi, prior.Constant)
        assert isinstance(sersic.intensity, prior.Constant)
        assert isinstance(sersic.effective_radius, prior.Constant)
        assert isinstance(sersic.sersic_index, prior.Constant)

    if os.path.exists(output_path):
        shutil.rmtree(output_path)
