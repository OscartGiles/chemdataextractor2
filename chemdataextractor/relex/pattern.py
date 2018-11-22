# -*- coding: utf-8 -*-
"""
chemdataextractor.relex.pattern.py
Extraction pattern object
"""
import re
from ..parse.elements import I, W, R, Any, And, Start, OneOrMore, Group


class Pattern:
    """ Pattern object, fundamentally the same as a phrase"""

    def __init__(self, entities=None,
                 elements=None,
                 label=None,
                 sentences=None,
                 order=None, relations=None):
        """

        :param entities: Dict containing the associated entities
        :param elements: Dict containing tokens and vectors for this pattern
        :param label: string associating this pattern to a cluster
        :param relations: known relations
        :param sentences: known sentences
        :param order: order of entities in the pattern
        :param specifier_regex:
        :param value_regex:
        :param unit_regex:
        """
        self.cluster_label = label
        self.elements = elements
        self.entities = entities
        self.number_of_entities = len(order)
        self.order = order
        self.relations = relations

    def __repr__(self):
        return self.to_string()
    
    def to_string(self):
        output_string = ''
        output_string += ' '.join(self.elements['prefix']['tokens']) + ' '
        output_string += self.entities[0].tag.name + ' '
        for i in range(0, self.number_of_entities - 1):
            output_string += ' '.join(self.elements['middle_' + str(i+1)]['tokens']) + ' '
            output_string += self.entities[i + 1].tag.name + ' '
        output_string = output_string[:-1]
        output_string += ' '.join(self.elements['suffix']['tokens'])

        return output_string
    
    def generate_cde_element(self):
        """Create a CDE parse element from the this extraction pattern
        """
        elements = []
        prefix_tokens = self.elements['prefix']['tokens']
        for token in prefix_tokens:
            elements.append(I(token))

        elements.append(self.entities[0].tag)
        
        for middle in range(0, self.number_of_entities -1):
            middle_tokens = self.elements['middle_' + str(middle+1)]['tokens']
            for token in middle_tokens:
                elements.append(I(token))
            elements.append(self.entities[middle+1].tag)
        
        suffix_tokens = self.elements['suffix']['tokens']
        for token in suffix_tokens:
            elements.append(I(token))
        
        final_phrase = And(exprs=elements)
        return (final_phrase)('phrase')
