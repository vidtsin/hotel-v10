# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

operators = ['from', 'to', 'not', 'and']
# rage_dict = []
a_filter = "from 5 to 6 not 7, 8 and 92,784".replace(',', ' ').replace(';', ' ')
a_list = [token for token in a_filter.split(' ') if token.isalnum()]

def parser(a_list, rage_dict):
    i = 0
    while i < len(a_list):
        if a_list[i].lower() == 'from':
            ini = a_list[i + 1]
            if a_list[i + 2].lower() != 'to':
                break;
            end = a_list[i + 3]
            rage_dict.append({'ini': ini, 'end': end})
            i += 4
        elif a_list[i].lower() in ['not', 'and']:
            i2 = i + 1
            account = []
            while i2 < len(a_list) and a_list[i2].lower() not in operators:
                account.append(a_list[i2])
                i2 += 1
            if not rage_dict:
                rage_dict.append({})
            if a_list[i].lower() == 'not':
                rage_dict[-1].update({'exclude': account})
            else:
                rage_dict[-1].update({'include': account})
            i = i2
        else:
            i += 1

