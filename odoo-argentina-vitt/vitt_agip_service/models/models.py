# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016  BACG S.A. de C.V.  (http://www.bacgroup.net)
#    All Rights Reserved.
#
##############################################################################

from odoo import models, fields, api, _
import os
import inspect
from odoo.tools.misc import file_open
from odoo.tools import config
import datetime
from odoo.exceptions import ValidationError, Warning

class RetPadron(models.Model):
    _name = "ret.padron"

    main_id_number = fields.Char(size=11,sting="CUIT/CUIL",index=True)
    issue_date = fields.Date(string="issue date",index=True)
    sdate = fields.Date(string="start date")
    edate = fields.Date(string="end date")
    type = fields.Selection([('C','contribuyente'),('D','convenio')])
    percep_rate = fields.Float(string="Perception Rate")
    whold_rate = fields.Float(string="Witholding Rate")
    percep_group = fields.Char(size=2,string="Percepcion Group")
    whold_group = fields.Char(size=2,string="Witholding Group")

    def get_txt_path(self):
        directory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)))
        return directory_path + '/../padron/padron.txt'

    def ex_import_padron(self):
        path = self.get_txt_path()
        print path
        try:
            rec = dict()
            fp = open(path, 'r')
        except:
            raise ValidationError(_('error abriendo archivo'))

        content = fp.readlines()
        content = [x.strip() for x in content]
        for i,line in enumerate(content):
            l = line.split(';')
            if i % 10000 == 0:
                print "ya importado " + str(i) + " lineas " + str(datetime.datetime.now())
            r = self.env['ret.padron'].search([
                ('issue_date','=',datetime.datetime.strptime(l[0], '%d%m%Y').date()),
                ('main_id_number','=',l[3])
            ])
            if not r:
                self.create({
                    'main_id_number': l[3],
                    'issue_date': datetime.datetime.strptime(l[0], '%d%m%Y').date(),
                    'sdate': datetime.datetime.strptime(l[1], '%d%m%Y').date(),
                    'edate': datetime.datetime.strptime(l[2], '%d%m%Y').date(),
                    'type': l[4],
                    'percep_rate': float(l[7].replace(',', '.')),
                    'whold_rate': float(l[8].replace(',', '.')),
                    'percep_group': l[9],
                    'whold_group': l[10]
                })
        fp.close()


