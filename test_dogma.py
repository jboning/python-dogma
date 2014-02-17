import os
import gc
import subprocess

from contextlib import contextmanager
from unittest import TestCase

import dogma

from test_dogma_values import *

class TestDogma(TestCase):
    def test(self):
        ctx = dogma.Context()

        self.assertEqual(ctx.get_location_attribute(dogma.Location.char(), ATT_MaxActiveDrones), 5.0)
        self.assertEqual(ctx.get_character_attribute(ATT_MaxActiveDrones), 5.0)

        slot = ctx.add_implant(TYPE_SnakeOmega)
        self.assertEqual(ctx.get_location_attribute(dogma.Location.implant(slot), ATT_Implantness), 6.0)
        ctx.remove_implant(slot)
        with self.assertRaises(dogma.NotFoundException):
            ctx.remove_implant(slot)

        ctx.set_default_skill_level(3)
        self.assertEqual(ctx.get_character_attribute(ATT_MaxActiveDrones), 3.0)
        ctx.set_skill_level(TYPE_Drones, 0)
        self.assertEqual(ctx.get_character_attribute(ATT_MaxActiveDrones), 0.0)
        self.assertEqual(ctx.get_skill_attribute(TYPE_Drones, ATT_SkillLevel), 0.0)
        ctx.reset_skill_levels()
        self.assertEqual(ctx.get_character_attribute(ATT_MaxActiveDrones), 3.0)
        self.assertEqual(ctx.get_location_attribute(dogma.Location.skill(TYPE_Drones), ATT_MaxActiveDroneBonus), 3.0)
        ctx.set_default_skill_level(5)
        self.assertEqual(ctx.get_character_attribute(ATT_MaxActiveDrones), 5.0)

        ctx.set_ship(TYPE_Rifter)
        self.assertEqual(ctx.get_ship_attribute(ATT_MaxLockedTargets), 4.0)
        ctx.set_ship(TYPE_Scimitar)
        self.assertEqual(ctx.get_ship_attribute(ATT_MaxLockedTargets), 10.0)

        slot = ctx.add_module(TYPE_SmallAncillaryShieldBooster)
        ctx.set_module_state(slot, dogma.State.OVERLOADED)
        self.assertGreater(ctx.get_module_attribute(slot, ATT_CapacitorNeed), 0.0)
        ctx.remove_module(slot)

        slot = ctx.add_module(TYPE_SmallAncillaryShieldBooster, state=dogma.State.ACTIVE)
        ctx.remove_module(slot)

        slot = ctx.add_module(TYPE_SmallAncillaryShieldBooster, charge=TYPE_CapBooster25)
        self.assertEqual(ctx.get_module_attribute(slot, ATT_CapacitorNeed), 0.0)
        ctx.remove_module(slot)

        slot = ctx.add_module(TYPE_SmallAncillaryShieldBooster, state=dogma.State.ONLINE, charge=TYPE_CapBooster25)
        self.assertEqual(ctx.get_module_attribute(slot, ATT_CapacitorNeed), 0.0)
        ctx.remove_charge(slot)
        self.assertGreater(ctx.get_module_attribute(slot, ATT_CapacitorNeed), 0.0)
        ctx.add_charge(slot, TYPE_CapBooster25)
        self.assertEqual(ctx.get_module_attribute(slot, ATT_CapacitorNeed), 0.0)
        self.assertEqual(ctx.get_charge_attribute(slot, ATT_CapacitorBonus), 25.0)
        ctx.remove_charge(slot)
        with self.assertRaises(dogma.NotFoundException):
            ctx.remove_charge(slot)
        ctx.remove_module(slot)

        with self.assertRaises(dogma.NotFoundException):
            ctx.remove_charge(slot)
        with self.assertRaises(dogma.NotFoundException):
            ctx.remove_module(slot)
        with self.assertRaises(dogma.NotFoundException):
            ctx.get_module_attribute(slot, ATT_CapacitorNeed)

        ctx.add_drone(TYPE_WarriorI, 2)
        self.assertEqual(ctx.get_drone_attribute(TYPE_WarriorI, ATT_DroneBandwidthUsed), 5.0)
        ctx.remove_drone_partial(TYPE_WarriorI, 1)
        self.assertEqual(ctx.get_location_attribute(dogma.Location.drone(TYPE_WarriorI), ATT_DroneBandwidthUsed), 5.0)
        ctx.remove_drone(TYPE_WarriorI)
        with self.assertRaises(dogma.NotFoundException):
            ctx.get_drone_attribute(TYPE_WarriorI, ATT_DroneBandwidthUsed)

        slot = ctx.add_implant(TYPE_StrongBluePillBooster)
        loc = dogma.Location.implant(slot)
        ctx.toggle_chance_based_effect(loc, EFFECT_BoosterShieldCapacityPenalty, True)
        self.assertEqual(ctx.get_chance_based_effect_chance(loc, EFFECT_BoosterShieldCapacityPenalty), 0.3)
        ctx.remove_implant(slot)
        with self.assertRaises(dogma.NotFoundException):
            ctx.toggle_chance_based_effect(loc, EFFECT_BoosterShieldCapacityPenalty, False)

        slot = ctx.add_module(TYPE_StasisWebifierI)
        loc = dogma.Location.module(slot)
        ctx.target(loc, ctx)
        ctx.clear_target(loc)
        ctx.remove_module(slot)

        fleet = dogma.FleetContext()
        
        fleet.add_fleet_commander(ctx)
        fleet.add_wing_commander(0, ctx)
        fleet.add_squad_commander(0, 0, ctx)
        fleet.add_squad_member(0, 0, ctx)

        self.assertTrue(fleet.remove_fleet_member(ctx))
        self.assertFalse(fleet.remove_fleet_member(ctx))
        fleet.add_squad_member(0, 0, ctx)

        fleet.set_fleet_booster(ctx)
        fleet.set_fleet_booster(None)
        fleet.set_wing_booster(0, ctx)
        fleet.set_wing_booster(0, None)
        fleet.set_squad_booster(0, 0, ctx)
        fleet.set_squad_booster(0, 0, None)

        # XXX this bit might not do what we want
        ctx = None
        fleet = None

        ctx = dogma.Context()
        fleet = dogma.FleetContext()
        fleet.add_squad_member(0, 0, ctx)

        fleet = None
        ctx = None

    def test_gc(self):
        def get_mem_usage():
            line = subprocess.check_output("pmap %d | grep total" % os.getpid(), shell=True)
            mem_str = line.strip().split()[-1]
            assert mem_str[-1] == "K"
            return int(mem_str[:-1]) * 1024

        @contextmanager
        def check_mem_usage(max_difference):
            start_usage = get_mem_usage()
            yield
            end_usage = get_mem_usage()
            self.assertLess(end_usage - start_usage, max_difference)

        with check_mem_usage(1 << 20):
            for i in xrange(1000):
                ctx = dogma.Context()

        with check_mem_usage(1 << 10):
            for i in xrange(10000):
                fleet = dogma.FleetContext()

        with check_mem_usage(1 << 10):
            for i in xrange(10000):
                affectors = ctx.get_affectors(dogma.Location.char())
