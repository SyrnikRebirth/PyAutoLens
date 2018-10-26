import os
import numpy as np

from autolens.galaxy import galaxy as g
from autolens.galaxy import galaxy_model as gm
from autolens.imaging import imaging_util
from autolens.imaging import scaled_array
from autolens.imaging import mask
from autolens.pipeline import phase as ph
from autolens.profiles import mass_profiles as mp
from test.integration import tools

dirpath = os.path.dirname(os.path.realpath(__file__))
dirpath = os.path.dirname(dirpath)
data_path = '{}/../datas/galaxy_fit'.format(dirpath)
output_path = '{}/../output/galaxy_fit'.format(dirpath)

def simulate_potential(data_name, pixel_scale, galaxy):

    image_shape = (150, 150)

    grids = mask.ImagingGrids.from_shape_and_pixel_scale(shape=image_shape, pixel_scale=pixel_scale)

    potential = galaxy.potential_from_grid(grid=grids.image)
    potential = imaging_util.map_unmasked_1d_array_to_2d_array_from_array_1d_and_shape(array_1d=potential,
                                                                                             shape=image_shape)

    if os.path.exists(output_path) == False:
        os.makedirs(output_path)

    imaging_util.numpy_array_to_fits(potential, path=data_path + data_name +'.fits', overwrite=True)

def setup_and_run_phase():

    data_name = '/potential'

    pixel_scale = 0.1

    tools.reset_paths(data_name=data_name, pipeline_name='', output_path=output_path)

    galaxy = g.Galaxy(sie=mp.EllipticalIsothermal(centre=(0.01, 0.01), axis_ratio=0.8, phi=80.0,
                                                        einstein_radius=1.6))

    simulate_potential(data_name=data_name, pixel_scale=pixel_scale, galaxy=galaxy)

    array_potential = \
        scaled_array.ScaledSquarePixelArray.from_fits_with_pixel_scale(file_path=data_path + data_name + '.fits',
                                                                       hdu=0, pixel_scale=pixel_scale)

    phase = ph.GalaxyFitPotentialPhase(dict(galaxy=gm.GalaxyModel(light=mp.EllipticalIsothermal)),
                              phase_name='potential')

    result = phase.run(array=array_potential, noise_map=np.ones(array_potential.shape))
    print(result)


if __name__ == "__main__":
    setup_and_run_phase()
