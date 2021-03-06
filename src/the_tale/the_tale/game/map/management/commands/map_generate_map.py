# coding: utf-8
import sys
import logging
import traceback

from django.core.management.base import BaseCommand

from the_tale.game.map.storage import map_info_storage
from the_tale.game.map.generator import update_map

logger = logging.getLogger('the-tale.workers.game_highlevel')

class Command(BaseCommand):

    help = 'generate map'

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument('-n', '--number', action='store', type=int, dest='repeate_number', default=1, help='howe many times do generation')

    def handle(self, *args, **options):

        try:
            for i in range(options['repeate_number']): # pylint: disable=W0612
                # print i
                update_map(index=map_info_storage.item.id+1)
        except Exception: # pylint: disable=W0703
            traceback.print_exc()
            logger.error('Map generation exception',
                         exc_info=sys.exc_info(),
                         extra={} )
