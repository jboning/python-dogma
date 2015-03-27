import weakref
from ctypes import *

# TODO: cross-platform support
libdogma = cdll.LoadLibrary("libdogma.so")


# datatypes

array_t       = pointer # to void
key_t         = c_ulong # Word_t from http://sourceforge.net/p/judy/code/HEAD/tree/trunk/src/Judy.h#l94
typeid_t      = c_uint32
attributeid_t = c_uint16
effectid_t    = c_int32

class LocationUnion(Union):
    _fields_ = [("implant_index", key_t),
                ("module_index", key_t),
                ("skill_typeid", typeid_t),
                ("drone_typeid", typeid_t)]

class Location(Structure):
    _fields_ = [("type", c_int),
                ("union", LocationUnion)]

    CHAR = 0
    IMPLANT = 1
    SKILL = 2
    SHIP = 3
    MODULE = 4
    CHARGE = 5
    DRONE = 6

    def __str__(self):
        value = ''
        if self.type == Location.IMPLANT:
            value = self.union.implant_index
        elif self.type in (Location.MODULE, Location.CHARGE):
            value = self.union.module_index
        elif self.type == Location.SKILL:
            value = self.union.skill_typeid
        elif self.type == Location.DRONE:
            value = self.union.drone_typeid
        return str(self.type)+':'+str(value)

    def __hash__(self):
        return hash(str(self))

    def __cmp__(self, other):
        if not isinstance(other, Location):
            raise Exception("invalid comparison")
        return cmp(str(self), str(other))

    @staticmethod
    def char():
        return Location(type=Location.CHAR)

    @staticmethod
    def implant(index):
        return Location(type=Location.IMPLANT,
                        union=LocationUnion(implant_index=index))

    @staticmethod
    def skill(typeid):
        return Location(type=Location.SKILL,
                        union=LocationUnion(skill_typeid=typeid))

    @staticmethod
    def ship():
        return Location(type=Location.SHIP)

    @staticmethod
    def module(index):
        return Location(type=Location.MODULE,
                        union=LocationUnion(module_index=index))

    @staticmethod
    def charge(index):
        return Location(type=Location.CHARGE,
                        union=LocationUnion(module_index=index))

    @staticmethod
    def drone(typeid):
        return Location(type=Location.DRONE,
                        union=LocationUnion(drone_typeid=typeid))


class State(object):
    UNPLUGGED = 0
    OFFLINE = 1
    ONLINE = 17
    ACTIVE = 31
    OVERLOADED = 63
state_t = c_int


# dogma-extra.h datatypes

AFFECTOR_PENALIZED = (1 << 0)
AFFECTOR_SINGLETON = (1 << 1)

class SimpleAffector(Structure):
    _fields_ = [("id", typeid_t),
                ("destid", attributeid_t),
                ("value", c_double),
                ("operator", c_char),
                ("order", c_uint8),
                ("flags", c_uint8)]

    def copy(self):
        data = dict((field, getattr(self, field)) for field, _ in self._fields_)
        return SimpleAffector(**data)

class SimpleCapacitorUnion(Union):
    _fields_ = [("stable_fraction", c_double),
                ("depletion_time", c_double)]

    def copy(self):
        return SimpleCapacitorUnion(stable_fraction=self.stable_fraction,
                                    depletion_time=self.depletion_time)

class SimpleCapacitor(Structure):
    _fields_ = [("context", POINTER(c_void_p)),
                ("capacity", c_double),
                ("delta", c_double),
                ("stable", c_bool),
                ("union", SimpleCapacitorUnion)]

    @property
    def stable_fraction(self):
        return self.union.stable_fraction

    @property
    def depletion_time(self):
        return self.union.depletion_time

    def copy(self):
        data = dict((field, getattr(self, field)) for field, _ in self._fields_)
        data['context'] = pointer(self.context.contents)
        data['union'] = self.union.copy()
        return SimpleCapacitor(**data)


# bindings

def _(x): return x

def accept_or_cast(typ, val):
    if isinstance(typ, type) and (isinstance(val, typ) or val is None):
        return val
    else:
        return typ(val)

def sig(*types):
    def wrap(f):
        def new_f(*values):
            casted = [accept_or_cast(typ, val) for typ, val in zip(types, values)]
            return f(*casted)
        new_f.func_name = f.func_name
        return new_f
    return wrap

OK = 0
NOT_FOUND = 1
NOT_APPLICABLE = 2

class DogmaException(Exception):
    pass

class NotFoundException(DogmaException):
    pass

class NotApplicableException(DogmaException):
    pass

def chk(ret):
    if ret == OK:
        return
    elif ret == NOT_FOUND:
        raise NotFoundException
    elif ret == NOT_APPLICABLE:
        raise NotApplicableException
    raise AssertionError("impossible return value %r" % ret)

chk(libdogma.dogma_init())

context_t = POINTER(c_void_p)
class Context(object):
    def __init__(self):
        self._as_parameter_ = context_t()
        
        self.targets_by_location = weakref.WeakValueDictionary()
        self.targeters = weakref.WeakSet()
        chk(libdogma.dogma_init_context(byref(self._as_parameter_)))

    def __del__(self):
        chk(libdogma.dogma_free_context(self))


    @sig(_, typeid_t)
    def add_implant(self, implant):
        slot = key_t()
        chk(libdogma.dogma_add_implant(self, implant, byref(slot)))
        return slot.value

    @sig(_, key_t)
    def remove_implant(self, slot):
        chk(libdogma.dogma_remove_implant(self, slot))


    @sig(_, c_uint8)
    def set_default_skill_level(self, level):
        chk(libdogma.dogma_set_default_skill_level(self, level))

    @sig(_, typeid_t, c_uint8)
    def set_skill_level(self, skill, level):
        chk(libdogma.dogma_set_skill_level(self, skill, level))

    def reset_skill_levels(self):
        chk(libdogma.dogma_reset_skill_levels(self))


    @sig(_, typeid_t)
    def set_ship(self, ship):
        chk(libdogma.dogma_set_ship(self, ship))


    def add_module(self, module, state=None, charge=None):
        accept_or_cast(typeid_t, module)
        if state:
            accept_or_cast(state_t, state)
        if charge:
            accept_or_cast(typeid_t, charge)

        slot = key_t()
        if state is None and charge is None:
            chk(libdogma.dogma_add_module(self, module, byref(slot)))
        elif charge is None:
            chk(libdogma.dogma_add_module_s(self, module, byref(slot), state))
        elif state is None:
            chk(libdogma.dogma_add_module_c(
                    self, module, byref(slot), charge))
        else:
            chk(libdogma.dogma_add_module_sc(
                    self, module, byref(slot), state, charge))
        return slot.value

    @sig(_, key_t)
    def remove_module(self, slot):
        chk(libdogma.dogma_remove_module(self, slot))

    @sig(_, key_t, state_t)
    def set_module_state(self, slot, state):
        chk(libdogma.dogma_set_module_state(self, slot, state))


    @sig(_, key_t, typeid_t)
    def add_charge(self, slot, charge):
        chk(libdogma.dogma_add_charge(self, slot, charge))

    @sig(_, key_t)
    def remove_charge(self, slot):
        chk(libdogma.dogma_remove_charge(self, slot))


    @sig(_, typeid_t, c_uint)
    def add_drone(self, drone, count):
        chk(libdogma.dogma_add_drone(self, drone, count))

    @sig(_, typeid_t, c_uint)
    def remove_drone_partial(self, drone, count):
        chk(libdogma.dogma_remove_drone_partial(self, drone, count))

    @sig(_, typeid_t)
    def remove_drone(self, drone):
        chk(libdogma.dogma_remove_drone(self, drone))


    @sig(_, Location, effectid_t, c_bool)
    def toggle_chance_based_effect(self, location, effect, on):
        chk(libdogma.dogma_toggle_chance_based_effect(
                self, location, effect, on))


    @sig(_, Location, _)
    def target(self, location, targetee):
        """Add a target."""
        self.targets_by_location[location] = targetee
        targetee.targeters.add(self)
        chk(libdogma.dogma_target(self, location, targetee))

    @sig(_, Location)
    def clear_target(self, location):
        targetee = self.targets_by_location[location]
        targetee.targeters.remove(self)
        chk(libdogma.dogma_clear_target(self, location))


    @sig(_, Location, attributeid_t)
    def get_location_attribute(self, location, attribute):
        result = c_double()
        chk(libdogma.dogma_get_location_attribute(
                self, location, attribute, byref(result)))
        return result.value

    @sig(_, attributeid_t)
    def get_character_attribute(self, attribute):
        result = c_double()
        chk(libdogma.dogma_get_character_attribute(
                self, attribute, byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_implant_attribute(self, implant, attribute):
        result = c_double()
        chk(libdogma.dogma_get_implant_attribute(
                self, implant, attribute, byref(result)))
        return result.value

    @sig(_, typeid_t, attributeid_t)
    def get_skill_attribute(self, skill, attribute):
        result = c_double()
        chk(libdogma.dogma_get_skill_attribute(
                self, skill, attribute, byref(result)))
        return result.value

    @sig(_, attributeid_t)
    def get_ship_attribute(self, attribute):
        result = c_double()
        chk(libdogma.dogma_get_ship_attribute(self, attribute, byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_module_attribute(self, module, attribute):
        result = c_double()
        chk(libdogma.dogma_get_module_attribute(
                self, module, attribute, byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_charge_attribute(self, charge, attribute):
        result = c_double()
        chk(libdogma.dogma_get_charge_attribute(
                self, charge, attribute, byref(result)))
        return result.value

    @sig(_, typeid_t, attributeid_t)
    def get_drone_attribute(self, drone, attribute):
        result = c_double()
        chk(libdogma.dogma_get_drone_attribute(
                self, drone, attribute, byref(result)))
        return result.value


    @sig(_, Location, effectid_t)
    def get_chance_based_effect_chance(self, location, effect):
        result = c_double()
        chk(libdogma.dogma_get_chance_based_effect_chance(
                self, location, effect, byref(result)))
        return result.value


    @sig(_, Location)
    def get_affectors(self, location):
        affectors = POINTER(SimpleAffector)()
        size = c_size_t()
        chk(libdogma.dogma_get_affectors(
                self, location, byref(affectors), byref(size)))
        result = [affectors[i].copy() for i in range(size.value)]
        libdogma.dogma_free_affector_list(affectors)
        return affectors

    @sig(_, key_t)
    def get_number_of_module_cycles_before_reload(self, slot):
        result = c_int()
        chk(libdogma.dogma_get_number_of_module_cycles_before_reload(
                self, slot, byref(result)))
        return result.value

    @sig(_, c_bool)
    def get_capacitor_all(self, include_reload_time):
        capacitors = POINTER(SimpleCapacitor)()
        size = c_size_t()

        chk(libdogma.dogma_get_capacitor_all(
                self, include_reload_time, byref(capacitors), byref(size)))
        capacitors_by_context = {}
        relevant_contexts = self.targeters.union(set(self.targets_by_location))
        relevant_contexts.add(self)
        assert len(relevant_contexts) == size.value
        for i in range(size.value):
            found = False
            for context in relevant_contexts:
                if (addressof(context._as_parameter_.contents) ==
                    addressof(capacitors[i].context.contents)):
                    assert not found
                    found = True
                    capacitors_by_context[context] = capacitors[i].copy()
            assert found
        libdogma.dogma_free_capacitor_list(capacitors)

        return capacitors_by_context

    @sig(_, Location, effectid_t)
    def get_location_effect_attributes(self, location, effect):
        duration = c_double()
        trackingspeed = c_double()
        discharge = c_double()
        range = c_double()
        falloff = c_double()
        fittingusagechance = c_double()
        chk(libdogma.dogma_get_location_effect_attributes(
            self, location, effect,
            byref(duration), byref(trackingspeed), byref(discharge),
            byref(range), byref(falloff), byref(fittingusagechance)))
        return (duration.value, trackingspeed.value, discharge.value,
                range.value, falloff.value, fittingusagechance.value)


fleet_context_t = POINTER(c_void_p)
class FleetContext(object):
    def __init__(self):
        self._as_parameter_ = fleet_context_t()
        chk(libdogma.dogma_init_fleet_context(byref(self._as_parameter_)))

    def __del__(self):
        chk(libdogma.dogma_free_fleet_context(self))


    @sig(_, Context)
    def add_fleet_commander(self, commander):
        chk(libdogma.dogma_add_fleet_commander(self, commander))

    @sig(_, key_t, Context)
    def add_wing_commander(self, wing, commander):
        chk(libdogma.dogma_add_wing_commander(self, wing, commander))

    @sig(_, key_t, key_t, Context)
    def add_squad_commander(self, wing, squad, commander):
        chk(libdogma.dogma_add_squad_commander(self, wing, squad, commander))

    @sig(_, key_t, key_t, Context)
    def add_squad_member(self, wing, squad, member):
        chk(libdogma.dogma_add_squad_member(self, wing, squad, member))


    @sig(_, Context)
    def remove_fleet_member(self, member):
        found = c_bool()
        chk(libdogma.dogma_remove_fleet_member(self, member, byref(found)))
        return found


    @sig(_, Context)
    def set_fleet_booster(self, booster):
        chk(libdogma.dogma_set_fleet_booster(self, booster))

    @sig(_, key_t, Context)
    def set_wing_booster(self, wing, booster):
        chk(libdogma.dogma_set_wing_booster(self, wing, booster))

    @sig(_, key_t, key_t, Context)
    def set_squad_booster(self, wing, squad, booster):
        chk(libdogma.dogma_set_squad_booster(self, wing, squad, booster))


@sig(typeid_t, state_t, effectid_t)
def type_has_effect(typ, state, effect):
    result = c_bool()
    chk(libdogma.dogma_type_has_effect(typ, state, effect, byref(result)))
    return result.value

@sig(typeid_t)
def type_has_active_effects(typ):
    result = c_bool()
    chk(libdogma.dogma_type_has_active_effects(typ, byref(result)))
    return result.value

@sig(typeid_t)
def type_has_overload_effects(typ):
    result = c_bool()
    chk(libdogma.dogma_type_has_overload_effects(typ, byref(result)))
    return result.value

@sig(typeid_t)
def type_has_projectable_effects(typ):
    result = c_bool()
    chk(libdogma.dogma_type_has_projectable_effects(typ, byref(result)))
    return result.value

@sig(typeid_t, attributeid_t)
def type_base_attribute(typ, attribute):
    result = c_double()
    chk(libdogma.dogma_type_base_attribute(typ, attribute, byref(result)))
    return result.value

@sig(typeid_t, c_uint)
def get_nth_type_effect_with_attributes(typ, n):
    result = effectid_t()
    chk(libdogma.dogma_get_nth_type_effect_with_attributes(typ, n, byref(result)))
    return result.value
