import os
import numpy as np

from autofit import conf
from autofit.optimize import non_linear as nl
from autolens.model.galaxy import galaxy as g, galaxy_model as gm
from autolens.model.galaxy import galaxy_data as gd
from autolens.model.galaxy.util import galaxy_util
from autolens.data.array import grids, scaled_array
from autolens.pipeline import phase as ph
from autolens.model.profiles import mass_profiles as mp
from test.integration import integration_util

test_type = 'galaxy_fit'
test_name = "potential"

test_path = '{}/../../'.format(os.path.dirname(os.path.realpath(__file__)))
output_path = test_path + 'output/'
config_path = test_path + 'config'
conf.instance = conf.Config(config_path=config_path, output_path=output_path)

def phase():

    pixel_scale = 0.1
    image_shape = (150, 150)

    integration_util.reset_paths(test_name=test_name, output_path=output_path)

    grid_stack = grids.GridStack.from_shape_pixel_scale_and_sub_grid_size(shape=image_shape, pixel_scale=pixel_scale,
                                                                          sub_grid_size=4)

    galaxy = g.Galaxy(mass=mp.SphericalIsothermal(centre=(0.0, 0.0), einstein_radius=1.0))

    potential = galaxy_util.potential_of_galaxies_from_grid(galaxies=[galaxy], grid=grid_stack.sub)
    potential = grid_stack.regular.scaled_array_2d_from_array_1d(array_1d=potential)

    noise_map = scaled_array.ScaledSquarePixelArray(array=np.ones(potential.shape), pixel_scale=pixel_scale)

    data = gd.GalaxyData(image=potential, noise_map=noise_map, pixel_scale=pixel_scale)

    phase = ph.GalaxyFitPhase(galaxies=dict(gal=gm.GalaxyModel(light=mp.SphericalIsothermal)), use_potential=True,
                              sub_grid_size=4,
                              optimizer_class=nl.MultiNest, phase_name=test_name+'/')

    phase.run(galaxy_data=[data])

if __name__ == "__main__":
    phase()