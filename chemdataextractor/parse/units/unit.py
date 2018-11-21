# -*- coding: utf-8 -*-
"""
chemdataextractor.units.unit.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Base types for making units.

Taketomo Isazawa (ti250@cam.ac.uk)

"""

import six
import copy
from abc import abstractmethod
from .dimensions import Dimensionless
from ...base_model import BaseModel, BaseType, FloatType, StringType, ListType


class UnitType(BaseType):
    """
    A field representing a Unit of some type.
    """

    def __set__(self, instance, value):
        """
        Make sure that any units assigned to models have the same dimensions
        as the model.
        """

        if hasattr(value, 'dimensions'):
            if value.dimensions == instance.dimensions:
                instance._values[self.name] = self.process(value)
            else:
                instance._values[self.name] = None
        else:
            instance._values[self.name] = None

    def process(self, value):

        if isinstance(value, Unit):
            return value
        return None

    def serialize(self, value, primitive=False):
        return str(value**1.0)

class MetaUnit(type):
    """
    Metaclass to ensure that all subclasses of Unit take the exponent into account
    when converting to standard units.
    """

    def __new__(cls, name, bases, attrs):
        instance = type.__new__(cls, name, bases, attrs)

        if hasattr(instance, 'convert_to_standard'):
            sub_convert_to_standard = getattr(instance, 'convert_to_standard')

            def new_convert_to_standard(self, value):
                val = value * 10**self.exponent
                return sub_convert_to_standard(self, val)
            setattr(instance, 'convert_to_standard', new_convert_to_standard)

        if hasattr(instance, 'convert_from_standard'):
            sub_convert_from_standard = getattr(instance, 'convert_from_standard')

            def new_convert_from_standard(self, value):
                val = value * 10**(-1 * self.exponent)
                return sub_convert_from_standard(self, val)
            setattr(instance, 'convert_from_standard', new_convert_from_standard)

        return instance


@six.add_metaclass(MetaUnit)
class Unit(object):
    """
    Object represeting units. Implement subclasses of this of basic units, e.g.
    units like meters, seconds, and Kelvins that are already implemented.
    These can then be combined by simply dividing or multiplying them to create
    more complex units. Alternatively, one can create these by subclassing Unit
    and setting the powers parameter as desired. For example, a speed could be
    represented as either:

    speedunit = Meter() / Second()

    or

    class SpeedUnit(Unit):

        def__init__(self, exponent=1.0):
            super(SpeedUnit, self).__init__(Length()/Time(),
                                            powers={Meter():1.0, Second():-1.0} )

    speedunit = SpeedUnit()

    and either method should produce the same results.
    """

    @classmethod
    def composite_unit(cls, with_units):
        """
        Creates a new Unit subclass composed of the units given.
        .. note::
            This returns a subclass of Unit, not an instance of a subclass of Unit.
        :param Unit with_units: The units for the new unit subclass to be created
        :returns: The new composite unit
        :rtype: subclass of Unit
        """
        new_unit = type(str(with_units), (cls, ), {})

        def new_initializer(self, exponent=with_units.exponent):
            Unit.__init__(with_units.dimensions, exponent, powers=with_units.powers)

        new_unit.__init__ = new_initializer
        return new_unit

    def __init__(self, dimensions, exponent=0.0, powers=None):
        """
        Creates a unit object. Subclass this to create concrete units. For examples,
        see lenghts.py and times.py

        :param Dimension dimensions: The dimensions this unit is for, e.g. Temperature
        :param float exponent: The exponent of the unit. e.g. km would be meters with an exponent of 3
        :param Dictionary{Unit : float} powers: For representing any more complicated units, e.g. m/s may have this parameter set to {Meter():1.0, Second():-1.0}
        """
        self.dimensions = dimensions
        self.exponent = exponent
        self.powers = powers

    def convert_value_to_standard(self, value):
        """
        Converts from this unit to the standard value, usually the SI unit.
        Overload this in child classes when implementing new units.

        :param float value: The value to convert to standard units
        """

        for unit, power in six.iteritems(self.powers):
            value = unit.convert_value_to_standard(value**(1 / power))**power
        return value

    def convert_value_from_standard(self, value):
        """
        Converts to this unit from the standard value, usually the SI unit.
        Overload this in child classes when implementing new units.

        :param float value: The value to convert from standard units
        """
        for unit, power in six.iteritems(self.powers):
            value = unit.convert_value_from_standard(value**(1 / power))**power
        return value

    def convert_error_to_standard(self, error):
        """
        Converts from this error to the standard value, usually the SI unit.
        Overload this in child classes when implementing new units

        :param float error: The error to convert to standard units
        :return float error: The error converted to standard units:
        """

        for unit, power in six.iteritems(self.powers):
            error = unit.convert_error_to_standard(error**(1 / power))**power
        return error

    def convert_error_from_standard(self, error):
        """
        Converts to this error from the standard value, usually the SI unit.
        Overload this in child classes when implementing new units

        :param float error: The error to convert from standard units
        :return float error: The error converted from standard units:
        """

        for unit, power in six.iteritems(self.powers):
            error = unit.convert_error_from_standard(error**(1 / power))**power
        return error


    """
    Operators are implemented for the easy creation of complicated units out of
    simpler, fundamental units. This means that every combination of exponents
    and units need not be accounted for.
    """

    def __truediv__(self, other):
        other_inverted = other**(-1.0)
        new_unit = self * other_inverted
        return new_unit

    def __pow__(self, other):

        # Handle dimensionless units so we don't get things like dimensionless units squared.
        if isinstance(self, DimensionlessUnit) or other == 0:
            new_unit = DimensionlessUnit(exponent=self.exponent * other)
            return new_unit

        powers = {}
        if self.powers:
            for key, value in six.iteritems(self.powers):
                powers[key] = self.powers[key] * other
        else:
            new_key = copy.deepcopy(self)
            new_key.exponent = 0.0
            powers[new_key] = other
        return Unit(self.dimensions**other, powers=powers, exponent=self.exponent * other)

    def __mul__(self, other):

        dimensions = self.dimensions * other.dimensions
        powers = {}
        # normalised_values is created as searching for keys won't always work
        # when the different units have different exponents, even though
        # they are essentially the same unit and they should be unified.
        normalised_values = {}
        exponent = self.exponent + other.exponent

        if self.powers:
            for key, value in six.iteritems(self.powers):
                powers[key] = self.powers[key]
                normalised_key = copy.deepcopy(key)
                normalised_key.exponent = 0.0
                normalised_values[normalised_key] = key.exponent

        else:
            if not isinstance(self, DimensionlessUnit):
                new_key = copy.deepcopy(self)
                new_key.exponent = 0.0
                powers[new_key] = 1.0
                normalised_values[new_key] = self.exponent

        if other.powers:
            for key, value in six.iteritems(other.powers):
                normalised_key = copy.deepcopy(key)
                normalised_key.exponent = 0.0
                if normalised_key in normalised_values.keys():
                    powers[key] += value
                    if powers[key] == 0:
                        powers.pop(key)
                else:
                    powers[normalised_key] = value

        else:
            if not isinstance(other, DimensionlessUnit):
                normalised_other = copy.deepcopy(other)
                normalised_other.exponent = 0.0
                if normalised_other in normalised_values:
                    powers[normalised_other] += 1.0
                    if powers[normalised_other] == 0:
                        powers.pop(other)
                else:
                    powers[normalised_other] = 1.0
        # powers.pop(DimensionlessUnit(), None)
        if len(powers) == 0:
            return DimensionlessUnit(exponent=exponent)

        return Unit(dimensions=dimensions, powers=powers, exponent=exponent)

    # eq and hash implemented so Units can be used as keys in dictionaries

    def __eq__(self, other):
        if not isinstance(other, Unit):
            return False
        if self.powers:
            if other.powers:
                if self.powers == other.powers and self.exponent == other.exponent:
                    return True
            else:
                if self.powers == (other**1.0).powers:
                    return True
        elif other.powers:
            if other.powers == (self**1.0).dimensions:
                return True
        else:
            if type(self) == type(other) and self.exponent == other.exponent and self.dimensions == other.dimensions:
                return True
        return False

    def __hash__(self):
        string = str(self.__class__.__name__)
        string += str(self.dimensions)
        string += str(float(self.exponent))
        string += str(self.powers)
        return string.__hash__()

    def __str__(self):
        string = ''
        if self.exponent != 0:
            string += '(10^' + str(self.exponent) + ') * '
        if self.powers is not None:
            for key, value in six.iteritems(self.powers):
                string += (type(key).__name__ + '^(' + str(value) + ')  ')
            string = string[:-2]
        else:
            string += type(self).__name__
        return string


class DimensionlessUnit(Unit):
    """Special case to handle dimensionless quantities."""

    def __init__(self, exponent = 0.0):
        self.dimensions = Dimensionless()
        self.exponent = exponent
        self.powers = None

    def convert_to_standard(self, value):
        return value

    def convert_from_standard(self, value):
        return value