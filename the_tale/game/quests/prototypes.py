# -*- coding: utf-8 -*-
from django_next.utils import s11n

from django_next.utils.decorators import nested_commit_on_success

from .models import Quest

def get_quest_by_id(id):
    try:
        return QuestPrototype(model=Quest.objects.get(id=id))
    except Quest.DoesNotExist:
        return None

def get_quest_by_model(model):
    return QuestPrototype(model=model)


class QuestPrototype(object):

    def __init__(self, model, *argv, **kwargs):
        super(QuestPrototype, self).__init__(*argv, **kwargs)
        self.model = model

    @property
    def id(self): return self.model.id

    @property
    def hero_id(self): return self.model.hero_id

    @property
    def percents(self): 
        return self.env.percents(self.pointer)

    @property
    def data(self):
        if not hasattr(self, '_data'):
            self._data = s11n.from_json(self.model.data)
        return self._data

    @property
    def env(self):
        from .logic import get_knowlege_base
        from .environment import Environment
        from .quests_generator.lines import BaseQuestsSource, BaseWritersSouece

        if not hasattr(self, '_env'):
            self._env = Environment(quests_source=BaseQuestsSource(),
                                    writers_source=BaseWritersSouece(),
                                    knowlege_base=get_knowlege_base())
            self._env.deserialize(s11n.from_json(self.model.env))
        return self._env

    def get_pointer(self): return self.data['pointer']
    def set_pointer(self, value):  self.data['pointer'] = value
    pointer = property(get_pointer, set_pointer)

    def get_last_pointer(self): return self.data.get('last_pointer', self.pointer)
    def set_last_pointer(self, value):  self.data['last_pointer'] = value
    last_pointer = property(get_last_pointer, set_last_pointer)

    @property
    def line(self): return self.data['line']

    @property
    def is_processed(self):
        return len(self.pos) == 0

    def get_choices(self):
        # MUST be always actual
        choices = {}
        choices_list = list(self.model.choices.all())
        for choice in choices_list:
            choices[choice.choice_point] = choice.choice
        return choices

    def make_choice(self, choice_point, choice):
        from .models import QuestChoice

        if QuestChoice.objects.filter(quest=self.model, choice_point=choice_point).exists():
            return False

        QuestChoice.objects.create(quest=self.model,
                                   choice_point=choice_point,
                                   choice=choice)

        return True

    ###########################################
    # Object operations
    ###########################################

    def remove(self): self.model.delete()
    def save(self): 
        self.model.data = s11n.to_json(self.data)
        self.model.env = s11n.to_json(self.env.serialize())
        self.model.save(force_update=True)

    @classmethod
    @nested_commit_on_success
    def create(cls, hero, env):

        env.sync()

        data = { 'pointer': env.get_start_pointer(),
                 'last_pointer': env.get_start_pointer()}

        if Quest.objects.filter(hero=hero.model).exists():
            raise Exception('Hero %s has already had quest' % hero.id)

        model = Quest.objects.create(hero=hero.model,
                                     env=s11n.to_json(env.serialize()),
                                     data=s11n.to_json(data))

        quest = QuestPrototype(model=model)

        quest.save()

        return quest


    def process(self, cur_action):
        
        if self.do_step(cur_action):
            return False, self.percents

        return True, 1

    def do_step(self, cur_action):
        
        self.process_current_command(cur_action)

        self.last_pointer = self.pointer
        self.pointer = self.env.increment_pointer(self.pointer, self.get_choices())

        if self.pointer is not None:
            return True

        self.end_quest()

        return False

    def end_quest(self):

        for person_id, power in self.env.persons_power_points.items():
            person_data = self.env.persons[person_id]
            from ..workers.environment import workers_environment
            workers_environment.highlevel.cmd_change_person_power(person_data['external_data']['id'], power * 100)
         
    def process_current_command(self, cur_action):

        cmd = self.env.get_command(self.pointer)

        writer = self.env.get_writer(self.pointer)

        log_msg = writer.get_log_msg(cmd.event)

        if log_msg:
            cur_action.hero.create_tmp_log_message(log_msg)

        {'description': self.cmd_description,
         'move': self.cmd_move,
         'movenear': self.cmd_move_near,
         'getitem': self.cmd_get_item,
         'giveitem': self.cmd_give_item,
         'getreward': self.cmd_get_reward,
         'quest': self.cmd_quest,
         'choose': self.cmd_choose,
         'givepower': self.cmd_give_power,
         'battle': self.cmd_battle
         }[cmd.type()](cmd, cur_action)

    def cmd_description(self, cmd, cur_action):
        cur_action.hero.create_tmp_log_message(cmd.msg)

    def cmd_move(self, cmd, cur_action):
        from ..actions.prototypes import ActionMoveToPrototype
        destination = self.env.get_game_place(cmd.place)
        cur_action.bundle.add_action(ActionMoveToPrototype.create(parent=cur_action, destination=destination, break_at=cmd.break_at))

    def cmd_move_near(self, cmd, cur_action):
        from ..actions.prototypes import ActionMoveNearPlacePrototype
        destination = self.env.get_game_place(cmd.place)
        cur_action.bundle.add_action(ActionMoveNearPlacePrototype.create(parent=cur_action, place=destination, back=cmd.back))

    def cmd_get_item(self, cmd, cur_action):
        item = self.env.get_game_item(cmd.item)
        cur_action.hero.put_loot(item)

    def cmd_give_item(self, cmd, cur_action):
        item = self.env.get_game_item(cmd.item)
        cur_action.hero.pop_quest_loot(item)

    def cmd_get_reward(self, cmd, cur_action):
        #TODO: implement
        cur_action.hero.create_tmp_log_message('hero get some reward [TODO: IMPLEMENT]')

    def cmd_quest(self, cmd, cur_action):
        # TODO: move to quest generator environment
        pass

    def cmd_choose(self, cmd, cur_action):
        # TODO: move to quest generator environment
        pass

    def cmd_give_power(self, cmd, cur_action):
        # TODO: move to quest generator environment
        if cmd.depends_on:
            self.env.persons_power_points[cmd.person] = self.env.persons_power_points[cmd.depends_on] * cmd.multiply
        else:
            self.env.persons_power_points[cmd.person] = cmd.power

    def cmd_battle(self, cmd, cur_action):
        from ..actions.prototypes import ActionBattlePvE_1x1Prototype
        from ..heroes.logic import create_mob_for_hero
        cur_action.bundle.add_action(ActionBattlePvE_1x1Prototype.create(parent=cur_action, mob=create_mob_for_hero(cur_action.hero)))

    def ui_info(self):
        choices = self.get_choices()

        cmd = self.env.get_nearest_quest_choice(self.pointer)
        quest = self.env.get_quest(self.pointer)
        writer = self.env.get_writer(self.pointer)

        if cmd:
            cmd_id = cmd.id
            if cmd.id in choices:
                choice_msg = writer.get_choice_result_msg(cmd.choice, choices[cmd.id])
            else:
                choice_msg = writer.get_choice_msg(cmd.choice)
        else:
            choice_msg = None
            cmd_id = None

        return {'line': self.env.get_writers_text_chain(self.last_pointer),
                'choice_id': cmd_id,
                'choice_text': choice_msg,
                'id': self.model.id,
                'subquest_id': quest.id}
