# coding: utf-8
from unittest import mock

from the_tale.amqp_environment import environment

from the_tale.common.utils import testcase

from the_tale.game.logic_storage import LogicStorage

from the_tale.game.logic import create_test_map

from the_tale.game import names

from the_tale.game.places import logic as places_logic

from the_tale.game.abilities.deck.building_repair import BuildingRepair

from the_tale.game.postponed_tasks import ComplexChangeTask
from the_tale.game.abilities.tests.helpers import UseAbilityTaskMixin


class BuildingRepairTest(UseAbilityTaskMixin, testcase.TestCase):
    PROCESSOR = BuildingRepair

    def setUp(self):
        super(BuildingRepairTest, self).setUp()

        self.place_1, self.place_2, self.place_3 = create_test_map()

        self.account_1 = self.accounts_factory.create_account()
        self.account_2 = self.accounts_factory.create_account(is_fast=True)

        self.storage = LogicStorage()
        self.storage.load_account_data(self.account_1)
        self.storage.load_account_data(self.account_2)

        self.hero_1 = self.storage.accounts_to_heroes[self.account_1.id]
        self.hero_2 = self.storage.accounts_to_heroes[self.account_2.id]

        self.ability_1 = self.PROCESSOR()
        self.ability_2 = self.PROCESSOR()

        environment.deinitialize()
        environment.initialize()

        self.highlevel = environment.workers.highlevel
        self.highlevel.process_initialize(0, 'highlevel')

        self.building = places_logic.create_building(self.place_1.persons[0], utg_name=names.generator().get_test_name('building-name'))
        self.building.integrity = 0.5
        places_logic.save_building(self.building)

    def use_attributes(self, hero, building_id=None, step=ComplexChangeTask.STEP.LOGIC, storage=None, highlevel=None, critical=False):
        return super(BuildingRepairTest, self).use_attributes(building_id=self.building.id if building_id is None else building_id, critical=critical, highlevel=highlevel, step=step, storage=storage, hero=hero)

    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', True)
    def test_use(self):

        with self.check_delta(lambda: self.hero_1.cards.help_count, 1):
            result, step, postsave_actions = self.ability_1.use(**self.use_attributes(hero=self.hero_1, storage=self.storage))

        self.assertEqual((result, step), (ComplexChangeTask.RESULT.CONTINUE, ComplexChangeTask.STEP.HIGHLEVEL))
        self.assertEqual(len(postsave_actions), 1)

        with mock.patch('the_tale.game.workers.highlevel.Worker.cmd_logic_task') as highlevel_logic_task_counter:
            postsave_actions[0]()

        self.assertEqual(highlevel_logic_task_counter.call_count, 1)

        self.assertEqual(self.building.integrity, 0.5)

        result, step, postsave_actions = self.ability_1.use(**self.use_attributes(hero=self.hero_1,
                                                                                  step=step,
                                                                                  highlevel=self.highlevel))

        self.assertEqual((result, step, postsave_actions), (ComplexChangeTask.RESULT.SUCCESSED, ComplexChangeTask.STEP.SUCCESS, ()))

        self.assertTrue(self.building.integrity > 0.5)


    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', True)
    @mock.patch('the_tale.game.heroes.objects.Hero.might_crit_chance', 1.0)
    def test_critical(self):

        use_attributes = self.use_attributes(hero=self.hero_1, storage=self.storage)

        result, step, postsave_actions = self.ability_1.use(**use_attributes)

        self.assertTrue(use_attributes['data']['critical'])

        self.assertEqual((result, step), (ComplexChangeTask.RESULT.CONTINUE, ComplexChangeTask.STEP.HIGHLEVEL))
        self.assertEqual(len(postsave_actions), 1)

        with mock.patch('the_tale.game.workers.highlevel.Worker.cmd_logic_task') as highlevel_logic_task_counter:
            postsave_actions[0]()

        self.assertEqual(highlevel_logic_task_counter.call_count, 1)

        self.assertEqual(self.building.integrity, 0.5)

        with mock.patch('the_tale.game.places.objects.Building.repair') as repair:
            result, step, postsave_actions = self.ability_1.use(**self.use_attributes(hero=self.hero_1,
                                                                                      step=step,
                                                                                      highlevel=self.highlevel,
                                                                                      critical=True))

        self.assertEqual(repair.call_count, 2)

        self.assertEqual((result, step, postsave_actions), (ComplexChangeTask.RESULT.SUCCESSED, ComplexChangeTask.STEP.SUCCESS, ()))

    def test_use_for_fast_account(self):
        self.assertEqual(self.building.integrity, 0.5)
        self.assertEqual(self.ability_2.use(**self.use_attributes(hero=self.hero_2, storage=self.storage)), (ComplexChangeTask.RESULT.FAILED, ComplexChangeTask.STEP.ERROR, ()))
        self.assertEqual(self.building.integrity, 0.5)

    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', False)
    def test_use_for_not_allowed_account(self):
        self.assertEqual(self.building.integrity, 0.5)
        self.assertEqual(self.ability_1.use(**self.use_attributes(hero=self.hero_1, storage=self.storage)), (ComplexChangeTask.RESULT.FAILED, ComplexChangeTask.STEP.ERROR, ()))
        self.assertEqual(self.building.integrity, 0.5)

    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', True)
    def test_use_for_repaired_building(self):
        self.building = places_logic.create_building(self.place_1.persons[0], utg_name=names.generator().get_test_name('building-name'))
        self.building.integrity = 1.0
        places_logic.save_building(self.building)

        self.assertEqual(self.ability_1.use(**self.use_attributes(hero=self.hero_1, storage=self.storage)), (ComplexChangeTask.RESULT.FAILED, ComplexChangeTask.STEP.ERROR, ()))

    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', True)
    def test_use_for_wrong_building_id(self):
        self.assertEqual(self.building.integrity, 0.5)
        self.assertEqual(self.ability_1.use(**self.use_attributes(hero=self.hero_1, building_id=666, storage=self.storage)), (ComplexChangeTask.RESULT.FAILED, ComplexChangeTask.STEP.ERROR, ()))
        self.assertEqual(self.building.integrity, 0.5)

    @mock.patch('the_tale.game.heroes.objects.Hero.can_repair_building', True)
    def test_use_without_building(self):
        self.assertEqual(self.building.integrity, 0.5)
        arguments = self.use_attributes(hero=self.hero_1, storage=self.storage)
        del arguments['data']['building_id']
        self.assertEqual(self.ability_1.use(**arguments), (ComplexChangeTask.RESULT.FAILED, ComplexChangeTask.STEP.ERROR, ()))
        self.assertEqual(self.building.integrity, 0.5)
