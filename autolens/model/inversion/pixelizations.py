import numpy as np
import scipy.spatial
import sklearn.cluster

from autolens import exc
from autolens.data.array import grids, scaled_array
from autolens.model.inversion import mappers
from autolens.model.inversion.util import pixelization_util


def setup_image_plane_pixelization_grid_from_galaxies_and_grid_stack(galaxies, grid_stack):
    """An image-plane pixelization is one where its pixel centres are computed by tracing a sparse grid of pixels from \
    the image's regular grid to other planes (e.g. the source-plane).

    Provided a galaxy has an image-plane pixelization, this function returns a new *GridStack* instance where the \
    image-plane pixelization's sparse grid is added to it as an attibute.

    Thus, when the *GridStack* are are passed to the *ray_tracing* module this sparse grid is also traced and the \
    traced coordinates represent the centre of each pixelization pixel.

    Parameters
    -----------
    galaxies : [model.galaxy.galaxy.Galaxy]
        A list of galaxies, which may contain pixelizations and an *ImagePlanePixelization*.
    grid_stacks : image.array.grid_stacks.GridStack
        The collection of grid_stacks (regular, sub, etc.) which the image-plane pixelization grid (referred to as pix) \
        may be added to.
    """
    if not isinstance(grid_stack.regular, grids.PaddedRegularGrid):
        for galaxy in galaxies:
            if hasattr(galaxy, 'pixelization'):
                if isinstance(galaxy.pixelization, ImagePlanePixelization):

                    image_plane_pix_grid = galaxy.pixelization.image_plane_pix_grid_from_regular_grid(
                        regular_grid=grid_stack.regular)
                    return grid_stack.new_grid_stack_with_pix_grid_added(pix_grid=image_plane_pix_grid.sparse_grid,
                                                                         regular_to_nearest_pix=image_plane_pix_grid.regular_to_sparse)

    return grid_stack


class ImagePlanePixelization(object):

    def __init__(self, shape):
        """An image-plane pixelization is one where its pixel centres are computed by tracing a sparse grid of pixels \
        from the image's regular grid to other planes (e.g. the source-plane).

        The traced coordinates of this sparse grid represent each centre of a pixelization pixel.

        See *grid_stacks.SparseToRegularGrid* for details on how this grid is calculated.

        Parameters
        -----------
        shape : (float, float) or (int, int)
            The shape of the image-plane pixelizaton grid in pixels (floats are converted to integers). The grid is \
            laid over the masked image such that it spans the most outer pixels of the masks.
        """
        self.shape = (int(shape[0]), int(shape[1]))

    def image_plane_pix_grid_from_regular_grid(self, regular_grid):
        """Calculate the image-plane pixelization from a regular-grid of coordinates (and its mask).

        See *grid_stacks.SparseToRegularGrid* for details on how this grid is calculated.

        Parameters
        -----------
        regular_grid : grids.RegularGrid
            The grid of (y,x) arc-second coordinates at the centre of every image value (e.g. image-pixels).
        """

        pixel_scale = regular_grid.mask.pixel_scale

        pixel_scales = ((regular_grid.masked_shape_arcsec[0] + pixel_scale) / (self.shape[0]),
                        (regular_grid.masked_shape_arcsec[1] + pixel_scale) / (self.shape[1]))

        return grids.SparseToRegularGrid(unmasked_sparse_grid_shape=self.shape, pixel_scales=pixel_scales,
                                         regular_grid=regular_grid, origin=regular_grid.mask.centre)


class Pixelization(object):

    def __init__(self):
        """ Abstract base class for a pixelization, which discretizes grid_stack of (y,x) coordinates into pixels.
        """

    def mapper_from_grid_stack_and_border(self, grid_stack, border):
        raise NotImplementedError("pixelization_mapper_from_grids_and_borders should be overridden")

    def __str__(self):
        return "\n".join(["{}: {}".format(k, v) for k, v in self.__dict__.items()])

    def __repr__(self):
        return "{}\n{}".format(self.__class__.__name__, str(self))


class Rectangular(Pixelization):

    def __init__(self, shape=(3, 3)):
        """A rectangular pixelization, where pixels are defined on a Cartesian and uniform grid of shape \ 
        (rows, columns).

        Like arrays, the indexing of the rectangular grid begins in the top-left corner and goes right and down.

        Parameters
        -----------
        shape : (int, int)
            The dimensions of the rectangular grid of pixels (y_pixels, x_pixel)
        """

        if shape[0] <= 2 or shape[1] <= 2:
            raise exc.PixelizationException('The rectangular pixelization must be at least dimensions 3x3')

        self.shape = (int(shape[0]), int(shape[1]))
        self.pixels = self.shape[0] * self.shape[1]
        super(Rectangular, self).__init__()

    class Geometry(scaled_array.RectangularArrayGeometry):

        def __init__(self, shape, pixel_scales, origin, pixel_neighbors, pixel_neighbors_size):
            """The geometry of a rectangular grid.

            This is used to map grid_stack of (y,x) arc-second coordinates to the pixels on the rectangular grid.

            Parameters
            -----------
            shape : (int, int)
                The dimensions of the rectangular grid of pixels (y_pixels, x_pixel)
            pixel_scales : (float, float)
                The pixel-to-arcsecond scale of a pixel in the y and x directions.
            origin : (float, float)
                The arc-second origin of the rectangular pixelization's coordinate system.
            pixel_neighbors : ndarray
                An array of length (y_pixels*x_pixels) which provides the index of all neighbors of every pixel in \
                the rectangular grid (entries of -1 correspond to no neighbor).
            pixel_neighbors_size : ndarrayy
                An array of length (y_pixels*x_pixels) which gives the number of neighbors of every pixel in the \
                rectangular grid.
            """
            self.shape = shape
            self.pixel_scales = pixel_scales
            self.origin = origin
            self.pixel_neighbors = pixel_neighbors.astype('int')
            self.pixel_neighbors_size = pixel_neighbors_size.astype('int')

        @property
        def pixel_centres(self):
            """The centre of every pixel in the rectangular pixelization."""
            return self.grid_1d

    def geometry_from_grid(self, grid, buffer=1e-8):
        """Determine the geometry of the rectangular grid, by overlaying it over a grid of coordinates such that its \
         outer-most pixels align with the grid's outer most coordinates plus a small buffer.

        Parameters
        -----------
        grid : ndarray
            The (y,x) grid of coordinates over which the rectangular pixelization is placed to determine its geometry.
        buffer : float
            The size the pixelization is buffered relative to the grid.
        """
        y_min = np.min(grid[:, 0]) - buffer
        y_max = np.max(grid[:, 0]) + buffer
        x_min = np.min(grid[:, 1]) - buffer
        x_max = np.max(grid[:, 1]) + buffer
        pixel_scales = (float((y_max - y_min) / self.shape[0]), float((x_max - x_min) / self.shape[1]))
        origin = ((y_max + y_min) / 2.0, (x_max + x_min) / 2.0)
        pixel_neighbors, pixel_neighbors_size = self.neighbors_from_pixelization()
        return self.Geometry(shape=self.shape, pixel_scales=pixel_scales, origin=origin,
                             pixel_neighbors=pixel_neighbors, pixel_neighbors_size=pixel_neighbors_size)

    def neighbors_from_pixelization(self):
        return pixelization_util.rectangular_neighbors_from_shape(shape=self.shape)

    def mapper_from_grid_stack_and_border(self, grid_stack, border):
        """Setup a rectangular mapper from a rectangular pixelization, as follows:

        1) If a border is supplied, relocate all of the grid-stack's regular and sub grid pixels beyond the border.
        2) Determine the rectangular pixelization's geometry, by laying the pixelization over the sub-grid.
        3) Setup the rectangular mapper from the relocated grid-stack and rectangular pixelization.

        Parameters
        ----------
        grid_stack : grids.GridStack
            A stack of grid describing the observed image's pixel coordinates (e.g. an image-grid, sub-grid, etc.).
        border : grids.RegularGridBorder | None
            The border of the grid-stack's regular-grid.
        """

        if border is not None:
            relocated_grid_stack = border.relocated_grid_stack_from_grid_stack(grid_stack)
        else:
            relocated_grid_stack = grid_stack

        geometry = self.geometry_from_grid(grid=relocated_grid_stack.sub)

        return mappers.RectangularMapper(pixels=self.pixels, grid_stack=relocated_grid_stack, border=border,
                                         shape=self.shape, geometry=geometry)


class Voronoi(Pixelization):

    def __init__(self):
        """Abstract base class for a Voronoi pixelization, which represents pixels as an irregular grid of Voronoi \
         cells which can form any shape, size or tesselation.

         The grid-stack's coordinates are paired to Voronoi pixels as the nearest-neighbors of the Voronoi \
        pixel-centers.
         """
        super(Voronoi, self).__init__()

    class Geometry(scaled_array.ArrayGeometry):

        def __init__(self, shape_arcsec, pixel_centres, origin, pixel_neighbors, pixel_neighbors_size):
            """The geometry of a Voronoi pixelization.

            Parameters
            -----------
            shape_arcsec : (float, float)
                The dimensions of the Voronoi grid ni arc-second (y_arcseconds, x_arcseconds)
            pixel_centres : ndarray
                The (y,x) centre of every Voronoi pixel in arc-seconds.
            origin : (float, float)
                The arc-second origin of the Voronoi pixelization's coordinate system.
            pixel_neighbors : ndarray
                An array of length (voronoi_pixels) which provides the index of all neighbors of every pixel in \
                the Voronoi grid (entries of -1 correspond to no neighbor).
            pixel_neighbors_size : ndarrayy
                An array of length (voronoi_pixels) which gives the number of neighbors of every pixel in the \
                Voronoi grid.
            """
            self.shape_arc_sec = shape_arcsec
            self.pixel_centres = pixel_centres
            self.origin = origin
            self.pixel_neighbors = pixel_neighbors.astype('int')
            self.pixel_neighbors_size = pixel_neighbors_size.astype('int')


    def geometry_from_grid(self, grid, pixel_centres, pixel_neighbors, pixel_neighbors_size, buffer=1e-8):
        """Determine the geometry of the Voronoi pixelization, by alligning it with the outer-most coordinates on a \
        grid plus a small buffer.

        Parameters
        -----------
        grid : ndarray
            The (y,x) grid of coordinates which determine the Voronoi pixelization's geometry.
        pixel_centres : ndarray
            The (y,x) centre of every Voronoi pixel in arc-seconds.
        origin : (float, float)
            The arc-second origin of the Voronoi pixelization's coordinate system.
        pixel_neighbors : ndarray
            An array of length (voronoi_pixels) which provides the index of all neighbors of every pixel in \
            the Voronoi grid (entries of -1 correspond to no neighbor).
        pixel_neighbors_size : ndarrayy
            An array of length (voronoi_pixels) which gives the number of neighbors of every pixel in the \
            Voronoi grid.
        """
        y_min = np.min(grid[:, 0]) - buffer
        y_max = np.max(grid[:, 0]) + buffer
        x_min = np.min(grid[:, 1]) - buffer
        x_max = np.max(grid[:, 1]) + buffer
        shape_arcsec = (y_max - y_min, x_max - x_min)
        origin = ((y_max + y_min) / 2.0, (x_max + x_min) / 2.0)
        return self.Geometry(shape_arcsec=shape_arcsec, pixel_centres=pixel_centres, origin=origin,
                             pixel_neighbors=pixel_neighbors, pixel_neighbors_size=pixel_neighbors_size)

    @staticmethod
    def voronoi_from_pixel_centers(pixel_centers):
        """Compute the Voronoi grid of the pixelization, using the pixel centers.

        Parameters
        ----------
        pixel_centers : ndarray
            The (y,x) centre of every Voronoi pixel.
        """
        return scipy.spatial.Voronoi(np.asarray([pixel_centers[:, 1], pixel_centers[:, 0]]).T,
                                     qhull_options='Qbb Qc Qx Qm')


    def neighbors_from_pixelization(self, pixels, ridge_points):
        """Compute the neighbors of every Voronoi pixel as an ndarray of the pixel index's each pixel shares a \
        vertex with.

        The ridge points of the Voronoi grid are used to derive this.

        Parameters
        ----------
        ridge_points : scipy.spatial.Voronoi.ridge_points
            Each Voronoi-ridge (two indexes representing a pixel mapping_matrix).
        """
        return pixelization_util.voronoi_neighbors_from_pixels_and_ridge_points(pixels=pixels,
                                                                                ridge_points=np.asarray(ridge_points))


class AdaptiveMagnification(Voronoi, ImagePlanePixelization):

    def __init__(self, shape=(3, 3)):
        """A pixelization which adapts to the magnification pattern of a lens's mass model and uses a Voronoi \
        pixelization to discretize the grid into pixels.

        Parameters
        ----------
        shape : (int, int)
            The shape of the unmasked sparse-grid which is laid over the masked image, in order to derive the \
            adaptive-magnification pixelization (see *ImagePlanePixelization*)
        """
        super(AdaptiveMagnification, self).__init__()
        ImagePlanePixelization.__init__(self=self, shape=shape)

    def mapper_from_grid_stack_and_border(self, grid_stack, border):
        """Setup a Voronoi mapper from an adaptive-magnification pixelization, as follows:

        1) (before this routine is called), setup the 'pix' grid as part of the grid-stack, which corresponds to a \
           sparse set of pixels in the image-plane which are traced to form the pixel centres.
        2) If a border is supplied, relocate all of the grid-stack's regular, sub and pix grid pixels beyond the border.
        3) Determine the adaptive-magnification pixelization's pixel centres, by extracting them from the relocated \
           pix grid.
        4) Use these pixelization centres to setup the Voronoi pixelization.
        5) Determine the neighbors of every Voronoi cell in the Voronoi pixelization.
        6) Setup the geometry of the pixelizatioon using the relocated sub-grid and Voronoi pixelization.
        7) Setup a Voronoi mapper from all of the above quantities.

        Parameters
        ----------
        grid_stack : grids.GridStack
            A collection of grid describing the observed image's pixel coordinates (includes an image and sub grid).
        border : grids.RegularGridBorder
            The borders of the grid_stacks (defined by their image-plane masks).
        """

        if border is not None:
            relocated_grids = border.relocated_grid_stack_from_grid_stack(grid_stack)
        else:
            relocated_grids = grid_stack

        pixel_centres = relocated_grids.pix
        pixels = pixel_centres.shape[0]

        voronoi = self.voronoi_from_pixel_centers(pixel_centres)

        pixel_neighbors, pixel_neighbors_size = self.neighbors_from_pixelization(pixels=pixels,
                                                                                 ridge_points=voronoi.ridge_points)
        geometry = self.geometry_from_grid(grid=relocated_grids.sub, pixel_centres=pixel_centres,
                                           pixel_neighbors=pixel_neighbors,
                                           pixel_neighbors_size=pixel_neighbors_size)

        return mappers.VoronoiMapper(pixels=pixels, grid_stack=relocated_grids, border=border,
                                     voronoi=voronoi, geometry=geometry)