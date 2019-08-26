# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __manifest__.py file in module root
# directory
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import UserError, Warning, RedirectWarning, ValidationError
import logging
_logger = logging.getLogger(__name__)


# class languaje(models.Model):
#     _name = "vitt_val2words.language"
#     name = fields.Char('Name', help='languaje', required=True)
#     description = fields.Char('Description', help='Languaje description', required=True)
#
#     _sql_constraints = [
#         ('value_languaje_uniq', 'unique (name)', 'Only one Languaje is permitted!')
#     ]


class val_to_word(models.Model):
    _name = "vitt_val2words.config_text"

    company_id = fields.Many2one('res.company', string='Company', help='code of company', required=True, index=1, default=lambda self: self.env.user.company_id.id, readonly=True)
    name = fields.Many2one('res.lang', string='Languaje', help='Languaje', required=True, oldname="languaje_id")
    config_numbers_id = fields.One2many('vitt_val2words.config_numbers', 'config_id', help='Numbers Config', required=True)
    currency_names_ids = fields.One2many('vitt_val2words.currency_names', 'config_id', help='Currency Names')
    bill1 = fields.Char('1 Billions', help='1 Billions')
    bill4 = fields.Char('2-4 Billions', help='2-4 Billions')
    bill9 = fields.Char('5-9 Billions', help='5-9 Billions')
    bill10 = fields.Char('Tens Billions', help='Tens Billions')
    mill1 = fields.Char('1 Millions', help='1 Millions')
    mill4 = fields.Char('2-4 Millions', help='2-4 Millions')
    mill9 = fields.Char('5-9 Millions', help='5-9 Millions')
    mill10 = fields.Char('Tens Millions', help='Tens Millions')
    thou1 = fields.Char('1 Thousands', help='1 Thousands')
    thou4 = fields.Char('2-4 Thousands', help='2-4 Thousands')
    thou9 = fields.Char('5-9 Thousands', help='5-9 Thousands')
    thou10 = fields.Char('Tens Thousands', help='Tens Thousands')
    houn1 = fields.Char('1 Hundreds', help='1 Hundreds')
    houn2 = fields.Char('2 Hundreds', help='2 Hundreds')
    houn3 = fields.Char('3 Hundreds', help='3 Hundreds')
    houn4 = fields.Char('4 Hundreds', help='4 Hundreds')
    houn5 = fields.Char('5 Hundreds', help='5 Hundreds')
    houn6 = fields.Char('6 Hundreds', help='6 Hundreds')
    houn7 = fields.Char('7 Hundreds', help='7 Hundreds')
    houn8 = fields.Char('8 Hundreds', help='8 Hundreds')
    houn9 = fields.Char('9 Hundreds', help='9 Hundreds')
    houn1single = fields.Char('One Hundred', help='One hundred only Conjunction')
    mainpart = fields.Char('Hundreds and Tens Conjunction', help='Hundreds and Tens Conjunction')
    decipart = fields.Char('Decimal Conjunction', help='Decimal Conjunction')
    endtext = fields.Char('Drag Text', help='Drag Text')
    zero = fields.Char('Zero Text', help='Zero Text')
    print_currency = fields.Selection([('after value', 'after Value'), ('before value', 'before value')], string='Print Currency', help='Print Currency', default="after value")
    dec_words = fields.Selection([('numbers', 'Numbers'), ('text', 'Text')], string='Decimal Words', help='Decimal Words', default="numbers")
    cutdecimals = fields.Boolean('Cut Decimals', help='Cut Decimals')
    negative = fields.Char(string='Negative Text')
    # val2words_config = fields.Boolean(related='company_id.val2words_config', default='company_id.val2words_config', store=False)

    _sql_constraints = [
        ('value_val_to_words_uniq', 'unique (company_id,name)', 'Only one Languaje is permitted per Company!')
    ]

    def more_than_999(self, words, a, b, c, unittext1, unittext4, unittext9):
        if (a + b + c == 1):
            if len(words) > 0:
                words = words + " "
            words = words + unittext1
        else:
            if ((c >= 2) and (c <= 4) and (b != 10)):
                if len(words) > 0:
                    words = words + " "
                words = words + unittext4
            else:
                if (a + b + c != 0):
                    if len(words) > 0:
                        words = words + " "
                    words = words + unittext9

        return words

    def to_word(self, num=0, kind=0):
        words = ""
        word = ""
        # logging.warning(num)
        n = int(num)
        a = (int(n / 100)) * 100
        b = (int((n - a) / 10)) * 10
        c = n - a - b

        # ------- (>=100 and <=999) -------
        if (a >= 100):
            temp = int(a / 100)
            if temp == 1:
                word = self.houn1
                if (b == 0 and c == 0):
                    if self.houn1single:
                        word = self.houn1single
                words = words + str(word)

            if temp == 2:
                words = words + self.houn2
            if temp == 3:
                words = words + self.houn3
            if temp == 4:
                words = words + self.houn4
            if temp == 5:
                words = words + self.houn5
            if temp == 6:
                words = words + self.houn6
            if temp == 7:
                words = words + self.houn7
            if temp == 8:
                words = words + self.houn8
            if temp == 9:
                words = words + self.houn9

        # ------- (<=99) -------
        temp = b + c
        if (temp >= 1) and (temp <= 99):
            if len(words) > 0:
                words = words + " "
            for l in self.config_numbers_id:
                if l.numtext == temp:
                    # lo conviento a str porque si esta en blanco es un boolean, causa exepcion
                    words = words + str(l.valtext)
                    break
        else:
            # (a%100!=0): Si las cifras arriba de cien son cerradas no llevan la palabra "cero"
            if (temp == 0) and (a % 100 != 0):
                if kind == -1:
                    words = words + " "
                    # words = words + self.decipart
                    words = words + " "
                    words = words + self.zero
                if kind == 0:
                    words = words + self.zero
            else:
                if kind == -1:
                    words = words + " "
                    # words = words + self.decipart
                    words = words + " "
                    words = words + self.zero

        # #------- (>=1000) -------
        if (kind == 1):
            words = self.more_than_999(words, a, b, c, self.thou1, self.thou4, self.thou9)

        if (kind == 2):
            words = self.more_than_999(words, a, b, c, self.mill1, self.mill4, self.mill9)

        if (kind == 3):
            words = self.more_than_999(words, a, b, c, self.bill1, self.bill4, self.bill9)

        return words

    # curncy=None,lang='es'
    def num_to_text(self, num=0, currency=None):
        currency = currency.get('symbol') or None
        return self.sudo()._num_to_text(num, currency)
        # return '10000'

    def _num_to_text(self, num=0, currency=None):
        # if not self.name:
        #     return " "
        is_negative = False
        if num < 0:
            is_negative = True

        num = abs(num)
        # Sólo acepto 2 decimales, en caso que se requiera mas agregar
        num_decimals = '{:,.2f}'.format(round(num, 2)).split('.')
        # logging.warning('VITT::      num_decimals:' + num_decimals[0])
        num_integer = num_decimals[0].split(',')
        num_decimals = num_decimals[1]

        sentence = ""
        bildval = ""
        mildval = ""
        thudval = ""
        hundval = ""
        decival = num_decimals
        # _logger.info("_NUM_TO_TEXT " + self.houn1single)
        # PARTE 1
        if len(num_integer) - 4 >= 0:
            bildval = num_integer[len(num_integer) - 4]
            if ((num != 1000) and (num != 1000000)):
                sentence = self.to_word(num=bildval, kind=3)
            if len(sentence) > 0:
                sentence = sentence + " "

        if len(num_integer) - 3 >= 0:
            mildval = num_integer[len(num_integer) - 3]
            sentence = sentence + self.to_word(num=mildval, kind=2)
            if len(sentence) > 0:
                sentence = sentence + " "

        if len(num_integer) - 2 >= 0:
            thudval = num_integer[len(num_integer) - 2]
            sentence = sentence + self.to_word(num=thudval, kind=1)
            if len(sentence) > 0:
                sentence = sentence + " "

        if len(num_integer) - 1 >= 0:
            hundval = num_integer[len(num_integer) - 1]
            if len(hundval) == 0:
                if num == 0:
                    hundval = self.zero
            sentence = sentence + self.to_word(num=hundval, kind=0)
            sentence = sentence + " "

        if len(sentence) > 0 and currency:
            sentence = sentence + currency

        if len(decival) > 0:
            if self.decipart:
                sentence = sentence + " " + str(self.decipart)

            if self.dec_words == "text":
                sentence = sentence + " " + self.to_word(decival, -1)
            else:
                sentence = sentence + " " + decival

            if self.endtext:
                sentence = sentence + " " + str(self.endtext)

        if is_negative and self.negative:
            sentence = self.negative + " " + sentence

        return sentence


class config_numbers(models.Model):
    _name = "vitt_val2words.config_numbers"
    company_id = fields.Many2one('res.company', string='Company', help='code of company', required=True, index=1, default=lambda self: self.env.user.company_id.id, readonly=True)
    config_id = fields.Many2one('vitt_val2words.config_text', string='Words Configuration', help='Words Configuration', required=True)
    numtext = fields.Integer('Number', help='Number', required=True)
    valtext = fields.Char('In word', help='In words')

    _sql_constraints = [
        ('value_config_numbers_uniq', 'unique (company_id, config_id, number)', 'Only one Number per Company is permitted!')
    ]


class CurrencyNames(models.Model):
    _name = "vitt_val2words.currency_names"

    config_id = fields.Many2one('vitt_val2words.config_text', string='Currency Names', help='Currency Names', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency')
    currency_name = fields.Char('Currency Name', help='Currency Name')

    _sql_constraints = [
        ('value_config_numbers_uniq', 'unique (currency_id, config_id)', 'Only one Currency per Config is permitted!')
    ]
