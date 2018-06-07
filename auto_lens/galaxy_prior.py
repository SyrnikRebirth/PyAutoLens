import random
import string
from auto_lens import galaxy
from auto_lens.model_mapper import Value
from auto_lens import exc


class GalaxyPrior:
    """
    Class to produce Galaxy instances from sets of profile classes using the model mapper
    """

    def __init__(self, light_profile_classes=None, mass_profile_classes=None, align_centres=False,
                 align_orientations=False):
        """
        Parameters
        ----------
        light_profile_classes: [LightProfile]
            The classes for which light profile instances are generated for this galaxy
        mass_profile_classes: [MassProfile]
            The classes for which light profile instances are generated for this galaxy
        align_centres: Bool
            If True the same prior will be used for all the profiles centres such that any generated profiles always
            have the same centre
        align_orientations: Bool
            If True the same prior will be used for all the profiles orientations such that any generated profiles
            always have the same orientation
        """
        self.id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

        self.light_profile_classes = light_profile_classes if light_profile_classes is not None else []
        self.mass_profile_classes = mass_profile_classes if mass_profile_classes is not None else []
        self.align_centres = align_centres
        self.align_orientations = align_orientations

    def attach_to_model_mapper(self, model_mapper):
        """
        Associate this instance with a given model_mapper, passing its internal classes to the model mapper to become
        priors.

        Parameters
        ----------
        model_mapper: ModelMapper
            A class used to generated instances from non-linear search hypercube vectors.

        Returns
        -------
        prior_models: [PriorModel]
            The prior models created to generate instances of the classes
        """
        profile_models = []

        for name, cls in zip(self.light_profile_names, self.light_profile_classes):
            profile_models.append(model_mapper.add_class(name, cls))

        for name, cls in zip(self.mass_profile_names, self.mass_profile_classes):
            profile_models.append(model_mapper.add_class(name, cls))

        if self.align_centres:
            centre = profile_models[0].centre
            for profile_model in profile_models:
                profile_model.centre = centre

        if self.align_orientations:
            phi = profile_models[0].phi
            for profile_model in profile_models:
                profile_model.phi = phi

        prior_models = profile_models + [model_mapper.add_class(self.redshift_name.format(self.id), Value)]

        return prior_models

    @property
    def light_profile_names(self):
        """
        Returns
        -------
        light_profile_names: [String]
            A list of names associated with the light profiles of this galaxy
        """
        return ["{}_light_profile_{}".format(self.id, num) for num in range(len(self.light_profile_classes))]

    @property
    def mass_profile_names(self):
        """
        Returns
        -------
        mass_profile_names: [String]
            A list of names associated with the mass profiles of this galaxy
        """
        return ["{}_mass_profile_{}".format(self.id, num) for num in range(len(self.mass_profile_classes))]

    @property
    def redshift_name(self):
        """
        Returns
        -------
        redshift_name: String
            The name of the prior associated with redshift for this galaxy.
        """
        return "{}_redshift".format(self.id)

    def galaxy_for_model_instance(self, model_instance):
        """
        Create a galaxy from a model instance that was generated by the associated model mapper.

        Parameters
        ----------
        model_instance: ModelInstance
            A model instance comprising the class instances generated by the model mapper.

        Returns
        -------
        galaxy: Galaxy
            A galaxy generated for this GalaxyPrior
        """
        light_profiles = []
        mass_profiles = []
        try:
            for name in self.light_profile_names:
                light_profiles.append(getattr(model_instance, name))
            for name in self.mass_profile_names:
                mass_profiles.append(getattr(model_instance, name))
            redshift = getattr(model_instance, self.redshift_name).value
        except AttributeError as e:
            raise exc.PriorException(*e.args)

        return galaxy.Galaxy(light_profiles=light_profiles, mass_profiles=mass_profiles, redshift=redshift)
