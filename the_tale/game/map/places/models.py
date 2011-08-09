from django.db import models

class TERRAIN:
    DESERT = '_'
    FOREST = 'f'
    GRASS = '.'
    SWAMP = 'w'

TERRAIN_CHOICES = ( (TERRAIN.DESERT, 'desert' ),
                    (TERRAIN.FOREST, 'forest'),
                    (TERRAIN.GRASS, 'grass'),
                    (TERRAIN.SWAMP, 'swamp') )

class PLACE_TYPE:
    CITY = 'city'

PLACE_CHOICES = ( (PLACE_TYPE.CITY, 'city'), )
    
class Place(models.Model):

    x = models.BigIntegerField(null=False)
    y = models.BigIntegerField(null=False)

    name = models.CharField(max_length=150, null=False)

    terrain = models.CharField(max_length=1, 
                               default=TERRAIN.GRASS, 
                               choices=TERRAIN_CHOICES, 
                               null=False)

    type = models.CharField(max_length=50, 
                            choices=PLACE_CHOICES, 
                            null=False) 

    subtype = models.CharField(max_length=50, 
                               choices=( ('UNDEFINED', 'undefined'), ), 
                               null=False) # orc city, goblin dungeon (specify how to display)

    size = models.IntegerField(null=False) # specify size of the place

    class Meta:
        ordering = ('name', )

    def __unicode__(self):
        return self.name

    def __repr__(self):
        return self.__unicode__()


class HeroPosition(models.Model):

    place = models.ForeignKey(Place, related_name='positions', null=True, default=None, blank=True)

    road = models.ForeignKey('roads.road', related_name='positions', null=True, default=None, blank=True)
    percents = models.FloatField(null=True, default=None, blank=True)
    invert_direction = models.NullBooleanField(default=False, null=True, blank=True)

    hero = models.OneToOneField('heroes.Hero', related_name='position')
