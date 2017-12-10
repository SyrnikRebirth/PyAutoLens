import pytest
import numpy as np
import analysis
import math

class TestSourcePlaneGeometry(object):

    class TestInit(object):

        def test__sets_correct_values(self):
            coordinates = [(1.0, 1.0), (0.0, 0.5)]

            source_plane = analysis.SourcePlane(coordinates)

            assert source_plane.coordinates == [(1.0, 1.0), (0.0, 0.5)]

    class TestCoordinatesToCentre(object):

        def test__source_plane_centre_zeros_by_default__no_shift(self):

            coordinates = (0.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates)

            coordinates_shift = source_plane.coordinates_to_centre(coordinates)

            assert coordinates_shift[0] == 0.0
            assert coordinates_shift[1] == 0.0

        def test__source_plane_centre_x_shift__x_shifts(self):
            coordinates = (0.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.5, 0.0))

            coordinates_shift = source_plane.coordinates_to_centre(source_plane.coordinates)

            assert coordinates_shift[0] == -0.5
            assert coordinates_shift[1] == 0.0

        def test__source_plane_centre_y_shift__y_shifts(self):
            coordinates = (0.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.5))

            coordinates_shift = source_plane.coordinates_to_centre(coordinates)

            assert coordinates_shift[0] == 0.0
            assert coordinates_shift[1] == -0.5

        def test__source_plane_centre_x_and_y_shift__x_and_y_both_shift(self):
            coordinates = (0.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.5, 0.5))

            coordinates_shift = source_plane.coordinates_to_centre(coordinates)

            assert coordinates_shift[0] == -0.5
            assert coordinates_shift[1] == -0.5

        def test__source_plane_centre_and_coordinates__correct_shifts(self):
            coordinates = (0.2, 0.4)

            source_plane = analysis.SourcePlane(coordinates, centre=(1.0, 0.5))

            coordinates_shift = source_plane.coordinates_to_centre(coordinates)

            assert coordinates_shift[0] == -0.8
            assert coordinates_shift[1] == pytest.approx(-0.1, 1e-5)

    class TestCoordinatesToRadius(object):
        def test__coordinates_overlap_source_plane_analysis__r_is_zero(self):
            coordinates = (0.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            assert source_plane.coordinates_to_radius(coordinates) == 0.0

        def test__x_coordinates_is_one__r_is_one(self):
            coordinates = (1.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            assert source_plane.coordinates_to_radius(coordinates) == 1.0

        def test__x_and_y_coordinates_are_one__r_is_root_two(self):
            coordinates = (1.0, 1.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            assert source_plane.coordinates_to_radius(coordinates) == pytest.approx(np.sqrt(2), 1e-5)

        def test__shift_x_coordinate_first__r_includes_shift(self):
            coordinates = (1.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(-1.0, 0.0))

            assert source_plane.coordinates_to_radius(coordinates) == pytest.approx(2.0, 1e-5)

        def test__shift_x_and_y_coordinates_first__r_includes_shift(self):
            coordinates = (3.0, 3.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(2.0, 2.0))

            assert source_plane.coordinates_to_radius(coordinates) == pytest.approx(math.sqrt(2.0), 1e-5)

    class TestCoordinatesAngleFromX(object):
        def test__angle_is_zero__angles_follow_trig(self):
            coordinates = (1.0, 0.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 0.0

        def test__angle_is_forty_five__angles_follow_trig(self):
            coordinates = (1.0, 1.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 45.0

        def test__angle_is_sixty__angles_follow_trig(self):
            coordinates = (1.0, 1.7320)

            source_plane = analysis.SourcePlane(coordinates)

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == pytest.approx(60.0, 1e-3)

        def test__top_left_quandrant__angle_goes_above_90(self):
            coordinates = (-1.0, 1.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 135.0

        def test__bottom_left_quandrant__angle_continues_above_180(self):
            coordinates = (-1.0, -1.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 225.0

        def test__bottom_right_quandrant__angle_flips_back_to_above_90(self):
            coordinates = (1.0, -1.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 315.0

        def test__include_source_plane_centre__angle_takes_into_accounts(self):

            coordinates = (2.0, 2.0)

            source_plane = analysis.SourcePlane(coordinates, centre=(1.0, 1.0))

            theta_from_x = source_plane.coordinates_angle_from_x(coordinates)

            assert theta_from_x == 45.0

class TestSourcePlane(object):
    
    class TestSetupBorder(object):
    
        def test__four_coordinates_in_circle__correct_border(self):
    
            coordinates = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
            border_mask = [True, True, True, True]
    
            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))
            source_plane.setup_border(border_mask)
    
            assert source_plane.border.coordinates == [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
            assert source_plane.border.radii == [1.0, 1.0, 1.0, 1.0]
            assert source_plane.border.thetas == [0.0, 90.0, 180.0, 270.0]
    
        def test__six_coordinates_two_masked__correct_border(self):
    
            coordinates = [(1.0, 0.0), (20., 20.), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (1.0, 1.0)]
            border_mask = [True, False, True, True, True, False]
    
            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))
            source_plane.setup_border(border_mask)
    
            assert source_plane.border.coordinates == [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
            assert source_plane.border.radii == [1.0, 1.0, 1.0, 1.0]
            assert source_plane.border.thetas == [0.0, 90.0, 180.0, 270.0]
    
        def test__test_other_thetas_radii(self):
    
            coordinates = [(2.0, 0.0), (20., 20.), (2.0, 2.0), (-1.0, -1.0), (0.0, -3.0), (1.0, 1.0)]
            border_mask = [True, False, True, True, True, False]
    
            source_plane = analysis.SourcePlane(coordinates, centre=(0.0, 0.0))
            source_plane.setup_border(border_mask)
    
            assert source_plane.border.coordinates == [(2.0, 0.0), (2.0, 2.0), (-1.0, -1.0), (0.0, -3.0)]
            assert source_plane.border.radii == [2.0, 2.0*math.sqrt(2), math.sqrt(2.0), 3.0]
            assert source_plane.border.thetas == [0.0, 45.0, 225.0, 270.0]

    class TestBorderPolynomial(object):

        def test__source_plane_centre_offset__coordinates_same_r_and_theta_shifted(self):
    
            coordinates = [(2.0, 1.0), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)]
            border_mask = [True, True, True, True]
    
            source_plane = analysis.SourcePlane(coordinates, centre=(1.0, 1.0))
            source_plane.setup_border(border_mask)
            source_plane.border.setup_polynomial(polynomial_degree=3)
    
            assert source_plane.border.coordinates == [(2.0, 1.0), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)]
            assert source_plane.border.radii == [1.0, 1.0, 1.0, 1.0]
            assert source_plane.border.thetas == [0.0, 90.0, 180.0, 270.0]
    
        def test__four_coordinates_in_circle__thetas_at_radius_are_each_coordinates_radius(self):
    
            coordinates = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0), (0.0, 0.0)]
            border_mask = [True, True, True, True, False]
    
            source_plane = analysis.SourcePlane(coordinates)
            source_plane.setup_border(border_mask)
            source_plane.border.setup_polynomial(polynomial_degree=3)
    
            assert source_plane.border.get_border_radius_at_theta(theta=0.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=90.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=180.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=270.0) == pytest.approx(1.0, 1e-3)
    
        def test__eight_coordinates_in_circle__thetas_at_each_coordinates_are_the_radius(self):
    
            coordinates = [(1.0, 0.0), (0.5*math.sqrt(2), 0.5*math.sqrt(2)), (0.0, 1.0), (-0.5*math.sqrt(2), 0.5*math.sqrt(2)),
                           (-1.0, 0.0),(-0.5*math.sqrt(2), -0.5*math.sqrt(2)), (0.0, -1.0), (0.5*math.sqrt(2), -0.5*math.sqrt(2))]
    
            border_mask = [True, True, True, True, True, True, True, True]
    
            source_plane = analysis.SourcePlane(coordinates)
            source_plane.setup_border(border_mask)
            source_plane.border.setup_polynomial(polynomial_degree=3)
    
            assert source_plane.border.get_border_radius_at_theta(theta=0.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=45.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=90.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=135.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=180.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=225.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=270.0) == pytest.approx(1.0, 1e-3)
            assert source_plane.border.get_border_radius_at_theta(theta=315.0) == pytest.approx(1.0, 1e-3)
    
        def test__eight_coordinates_in_circle__move_factors_correct(self):
    
            coordinates = [(1.0, 0.0), (0.5*math.sqrt(2), 0.5*math.sqrt(2)), (0.0, 1.0), (-0.5*math.sqrt(2), 0.5*math.sqrt(2)),
                           (-1.0, 0.0),(-0.5*math.sqrt(2), -0.5*math.sqrt(2)), (0.0, -1.0), (0.5*math.sqrt(2), -0.5*math.sqrt(2))]
    
            border_mask = [True, True, True, True, True, True, True, True]
    
            source_plane = analysis.SourcePlane(coordinates)
            source_plane.setup_border(border_mask)
            source_plane.border.setup_polynomial(polynomial_degree=3)
    
        #    assert source_plane.border.get_move_factor(theta=0.0, )

class TestSourcePlaneBorder(object):

    class TestInit(object):

        def test__sets_correct_values(self):

            coordinates = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]

            source_border = analysis.SourcePlaneBorder(coordinates, centre=(0.0, 0.0))

            assert source_border.coordinates == [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]
            assert source_border.radii == [1.0, 1.0, 1.0, 1.0]
            assert source_border.thetas == [0.0, 90.0, 180.0, 270.0]

        def test__including_shift_sets_correct_values(self):

            coordinates = [(2.0, 1.0), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)]

            source_border = analysis.SourcePlaneBorder(coordinates, centre=(1.0, 1.0))

            assert source_border.coordinates == [(2.0, 1.0), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)]
            assert source_border.radii == [1.0, 1.0, 1.0, 1.0]
            assert source_border.thetas == [0.0, 90.0, 180.0, 270.0]

    class TestMoveFactors(object):

        # TODO : Work out some more test cases

        def test__inside_border__move_factor_is_1(self):

            coordinates = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]

            source_border = analysis.SourcePlaneBorder(coordinates, centre=(0.0, 0.0))
            source_border.setup_polynomial(polynomial_degree=3)
            assert source_border.get_move_factor(coordinate=(0.5, 0.0)) == 1.0
            assert source_border.get_move_factor(coordinate=(-0.5, 0.0)) == 1.0
            assert source_border.get_move_factor(coordinate=(0.25, 0.25)) == 1.0
            assert source_border.get_move_factor(coordinate=(0.0, 0.0)) == 1.0

        def test__outside_border_double_its_radius__move_factor_is_05(self):

            coordinates = [(1.0, 0.0), (0.0, 1.0), (-1.0, 0.0), (0.0, -1.0)]

            source_border = analysis.SourcePlaneBorder(coordinates, centre=(0.0, 0.0))
            source_border.setup_polynomial(polynomial_degree=3)
            assert source_border.get_move_factor(coordinate=(2.0, 0.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(0.0, 2.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(-2.0, 0.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(0.0, -2.0)) == pytest.approx(0.5, 1e-3)

        def test__outside_border_double_its_radius_and_offset__move_factor_is_05(self):

            coordinates = [(2.0, 1.0), (1.0, 2.0), (0.0, 1.0), (1.0, 0.0)]

            source_border = analysis.SourcePlaneBorder(coordinates, centre=(1.0, 1.0))
            source_border.setup_polynomial(polynomial_degree=3)
            assert source_border.get_move_factor(coordinate=(3.0, 1.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(1.0, 3.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(1.0, 3.0)) == pytest.approx(0.5, 1e-3)
            assert source_border.get_move_factor(coordinate=(3.0, 1.0)) == pytest.approx(0.5, 1e-3)

    class TestRelocate(object):

        # TODO : Work out some more test cases

        def test__outside_border_simple_cases__relocates_to_correct_coordinate(self):

            thetas = np.linspace(0.0, 2.0*np.pi, 32)
            circle = list(map(lambda x : (np.cos(x), np.sin(x)), thetas))

            source_border = analysis.SourcePlaneBorder(circle, centre=(0.0, 0.0))
            source_border.setup_polynomial(polynomial_degree=3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(2.0, 0.0))
            assert relocated_coordinate == pytest.approx((1.0, 0.0), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(1.0, 1.0))
            assert relocated_coordinate == pytest.approx((0.5*math.sqrt(2), 0.5*math.sqrt(2)), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(0.0, 2.0))
            assert relocated_coordinate == pytest.approx((0.0, 1.0), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(-1.0, 1.0))
            assert relocated_coordinate == pytest.approx((-0.5*math.sqrt(2), 0.5*math.sqrt(2)), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(-2.0, 0.0))
            assert relocated_coordinate == pytest.approx((-1.0, 0.0), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(-1.0, -1.0))
            assert relocated_coordinate == pytest.approx((-0.5*math.sqrt(2), -0.5*math.sqrt(2)), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(0.0, -1.0))
            assert relocated_coordinate == pytest.approx((0.0, -1.0), 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(1.0, -1.0))
            assert relocated_coordinate == pytest.approx((0.5*math.sqrt(2), -0.5*math.sqrt(2)), 1e-3)

        def test__outside_border__relocates_to_source_border(self):

            thetas = np.linspace(0.0, 2.0*np.pi, 32)
            circle = list(map(lambda x : (np.cos(x), np.sin(x)), thetas))

            source_border = analysis.SourcePlaneBorder(circle, centre=(0.0, 0.0))
            source_border.setup_polynomial(polynomial_degree=3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(2.5, 0.37))
            assert source_border.coordinates_to_radius(relocated_coordinate) == pytest.approx(1.0, 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(25.3, -9.2))
            assert source_border.coordinates_to_radius(relocated_coordinate) == pytest.approx(1.0, 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(13.5, 0.0))
            assert source_border.coordinates_to_radius(relocated_coordinate) == pytest.approx(1.0, 1e-3)

            relocated_coordinate = source_border.get_relocated_coordinate(coordinate=(-2.5, -0.37))
            assert source_border.coordinates_to_radius(relocated_coordinate) == pytest.approx(1.0, 1e-3)


