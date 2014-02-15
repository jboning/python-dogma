from ctypes import *

# TODO: cross-platform support
libdogma = cdll.LoadLibrary("libdogma.so")
libdogma.dogma_init()

OK = 0
NOT_FOUND = 1
NOT_APPLICABLE = 2

class DogmaException(Exception):
    pass

class NotFoundException(DogmaException):
    pass

class NotApplicableException(DogmaException):
    pass


# datatypes

array_t       = pointer # to void
key_t         = c_int # XXX check this, it's a Word_t
typeid_t      = c_uint32
attributeid_t = c_uint16
effectid_t    = c_int32

# XXX watch out enum
class LocationType(object):
    CHAR = 1
    IMPLANT = 2
    SKILL = 3
    SHIP = 4
    MODULE = 5
    CHARGE = 6
    DRONE = 7

class LocationUnion(Union):
    _fields_ = [("implant_index", key_t),
                ("module_index", key_t),
                ("skill_typeid", typeid_t),
                ("drone_typeid", typeid_t)]

class Location(Structure):
    _fields_ = [("type", c_int),
                ("union", LocationUnion)]

# XXX watch out enum
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

class FinalizableSizeablePointer(pointer):
    def __init__(self, *args, **kw):
        super(FinalizablePointer, self).__init__(*args, **kw)
        self.finalizer = None
        self.size = None

    def __finalize__(self):
        if self.finalizer:
            self.finalizer(self)
        super(FinalizablePointer, self).__finalize__()

    def __len__(self):
        if self.size is not None:
            return self.size
        return NotImplemented

class SimpleCapacitorUnion(Union):
    _fields_ = [("stable_fraction", c_double),
                ("depletion_time", c_double)]

class SimpleCapacitor(Structure)
    _fields_ = [("context", pointer),
                ("capacity", c_double),
                ("delta", c_double),
                ("stable", c_bool),
                ("union", SimpleCapacitorUnion)]


def _(x): return x

def accept_or_cast(typ, val):
    if isinstance(typ, type) and isinstance(val, typ):
        return val
    else:
        return typ(val)

def sig(*types):
    def wrap(f):
        def fprime(*values):
            casted = [accept_or_cast(typ, val) for typ, val in zip(types, values)]
            return f(*casted)
        return fprime
    return wrap

def chk(ret):
    if ret == OK:
        return
    elif ret == NOT_FOUND:
        raise NotFoundException
    elif ret == NOT_APPLICABLE:
        raise NotApplicableException
    raise AssertionError("impossible return value %r" % ret)


class Context(object):
    def __init__(self):
        self._as_parameter_ = pointer(c_void_p())
        chk(libdogma.dogma_init_context(byref(self._as_parameter_)))

    def __finalize__(self):
        chk(libdogma.dogma_free_context(self))


    @sig(_, typeid_t)
    def add_implant(self, implant):
        slot = key_t()
        chk(libdogma.dogma_add_implant(self, implant, byref(slot)))
        return slot.value

    @sig(_, key_t)
    def remove_implant(self, slot):
        chk(libdogma.dogma_remove_implant(key_t(slot)))


    @sig(_, c_uint8)
    def set_default_skill_level(self, level):
        chk(libdogma.dogma_set_default_skill_level(self, level))

    @sig(_, typeid_t, c_uint8)
    def set_skill_level(self, skill, level):
        chk(libdogma.dogma_set_default_skill_level(self, skill, level))

    @sig(_, typeid_t)
    def reset_skill_level(self, skill):
        chk(libdogma.dogma_reset_default_skill_level(self, skill))


    @sig(_, typeid_t)
    def set_ship(self, ship):
        chk(libdogma.dogma_set_ship(self, ship))


    @sig(_, typeid_t, state_t, typeid_t)
    def add_module(self, module, state=None, charge=None):
        slot = key_t()
        if state is None and charge is None:
            chk(libdogma.dogma_add_module(self, module, byref(slot)))
        elif charge is None:
            chk(libdogma.dogma_add_module_s(self, module, byref(slot), state))
        elif state is None:
            chk(libdogma.dogma_add_module_c(self, module, byref(slot),
                                            charge))
        else:
            chk(libdogma.dogma_add_module_sc(self, module, byref(slot), state,
                                             charge))
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
        chk(libdogma.dogma_remove_drone_partial(self, drone, c_uint(count)))

    @sig(_, typeid_t)
    def remove_drone(self, drone):
        chk(libdogma.dogma_remove_drone(self, drone))


    @sig(_, Location, effectid_t, c_bool)
    def toggle_chance_based_effect(self, location, effect, on):
        chk(libdogma.dogma_toggle_chance_based_effect(self, location, effect,
                                                      on))


    @sig(_, Location, _)
    def target(self, location, targetee):
        chk(libdogma.dogma_target(self, location, targetee))

    @sig(_, Location)
    def clear_target(self, location):
        chk(libdogma.dogma_clear_target(self, location))


    @sig(_, Location, attributeid_t)
    def get_location_attribute(self, location, attribute):
        result = c_double()
        chk(libdogma.dogma_get_location_attribute(self, location, attribute,
                                                  byref(value)))
        return result.value

    @sig(_, attributeid_t)
    def get_character_attribute(self, attribute):
        result = c_double()
        chk(libdogma.dogma_get_character_attribute(self, attribute,
                                                   byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_implant_attribute(self, implant, attribute):
        result = c_double()
        chk(libdogma.dogma_get_implant_attribute(self, implant, attribute,
                                                 byref(result)))
        return result.value

    @sig(_, typeid_t, attributeid_t)
    def get_skill_attribute(self, skill, attribute):
        result = c_double()
        chk(libdogma.dogma_get_skill_attribute(self, skill, attribute,
                                               byref(result)))
        return result.value

    @sig(_, attributeid_t)
    def get_ship_attribute(self, attribute):
        result = c_double()
        chk(libdogma.dogma_get_ship_attribute(self, attribute, byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_module_attribute(self, module, attribute):
        result = c_double()
        chk(libdogma.dogma_get_module_attribute(self, module, attribute,
                                                byref(result)))
        return result.value

    @sig(_, key_t, attributeid_t)
    def get_charge_attribute(self, charge, attribute):
        result = c_double()
        chk(libdogma.dogma_get_charge_attribute(self, charge, attribute,
                                                byref(result)))
        return result.value

    @sig(_, typeid_t, attributeid_t)
    def get_drone_attribute(self, drone, attribute):
        result = c_double()
        chk(libdogma.dogma_get_drone_attribute(self, drone, attribute,
                                               byref(result)))
        return result.value


    @sig(_, Location, effectid_t)
    def get_chance_based_effect_chance(self, location, effect):
        result = c_double()
        chk(libdogma.dogma_get_chance_based_effect_chance(self, drone,
                                                          attribute,
                                                          byref(result)))
        return result.value


    @sig(_, Location)
    def get_affectors(self, location):
        affectors = FinalizableSizeablePointer(c_void_p())
        affectors.finalizer = lambda ptr: libdogma.dogma_free_affector_list(ptr)
        size = c_size_t
        chk(libdogma.dogma_get_affectors(self, location, byref(affectors),
                                         byref(size)))
        affectors.size = size.value
        return affectors


    @sig(_, c_bool)
    def get_capacitor_all(self, include_reload_time):
        capacitor = FinalizableSizeablePointer(c_void_p())
        capacitor.finalizer = lambda ptr: libdogma.dogma_free_capacitor_list(ptr)
        size = c_size_t
        chk(libdogma.dogma_get_capacitor_all(self, include_reload_time,
                                             byref(capacitor), byref(size)))
        capacitor.size = size.value
        return capacitor

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
            duration, trackingspeed, discharge,
            range, falloff, fittingusagechance))
        return (duration.value, trackingspeed.value, discharge.value,
                range.value, falloff.value, fittingusagechance.value)

class FleetContext(object):
    def __init__(self):
        self._as_parameter_ = pointer(None)
        chk(libdogma.dogma_init_fleet_context(byref(self._as_parameter_)))

    def __finalize__(self):
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
