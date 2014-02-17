from unittest import TestCase

import dogma

from test_dogma_values import *

class TestDogmaExtra(TestCase):
    def test(self):
        ctx = dogma.Context()

        slot = ctx.add_module(TYPE_125mmGatlingAutoCannonII)
        loc = dogma.Location.module(slot)
        affectors = ctx.get_affectors(loc)

        ctx.set_ship(TYPE_Rifter)
        affectors_with_ship = ctx.get_affectors(loc)

        self.assertTrue(dogma.type_has_effect(TYPE_125mmGatlingAutoCannonII, dogma.State.ONLINE, EFFECT_HiPower))
        self.assertTrue(dogma.type_has_active_effects(TYPE_125mmGatlingAutoCannonII))
        self.assertTrue(dogma.type_has_overload_effects(TYPE_125mmGatlingAutoCannonII))
        self.assertTrue(dogma.type_has_projectable_effects(TYPE_StasisWebifierI))
        self.assertEqual(dogma.type_base_attribute(TYPE_Rifter, ATT_LauncherSlotsLeft), 2)

        ctx.add_charge(slot, TYPE_BarrageS)
        self.assertEqual(ctx.get_number_of_module_cycles_before_reload(slot), 200)

        effect = dogma.get_nth_type_effect_with_attributes(TYPE_125mmGatlingAutoCannonII, 0)
        (duration, tracking, discharge, att_range, falloff, usagechance,
                ) = ctx.get_location_effect_attributes(loc, effect)
        self.assertEqual(falloff, 7500)
        self.assertEqual(att_range, 1200)
        self.assertEqual(discharge, 0)


        capacitors = ctx.get_capacitor_all(False)
        self.assertEqual(len(capacitors), 1)
        self.assertIn(ctx, capacitors)
