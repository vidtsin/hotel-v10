# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

import time
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
from odoo import models, fields, api, _
from odoo.osv import expression
from odoo.exceptions import ValidationError


class HotelHousekeeper(models.Model):
    _name = 'hotel.housekeeper'

    employee_id = fields.Many2one('hr.employee', 'Housekepeer',
                                  required=True, delegate=True,
                                  ondelete='cascade')


class HouseKeepingSchedule(models.Model):
    _name = 'house.keeping.schedule'

    room_id = fields.Many2one('hotel.room', '')
    room_number_id = fields.Many2one('hotel.room.number', 'Room Number',
                                     required=True)

class HotelHousekeepingActivity(models.Model):

    _name = 'hotel.housekeeping.activity'
    _description = 'Housekeeping Activity'

    product_id = fields.Many2one('product.product', 'Product',
                                 required=True, delegate=True,
                                 ondelete='cascade', index=True)


class HotelHousekeepingStatusLog(models.Model):

    _name = 'hotel.housekeeping.status.log'

    log_date = fields.Datetime('Log Datetime')
    room_number_id = fields.Many2one('hotel.room.number', 'Room Number',
                                     required=True)
    state = fields.Selection([('clean', 'Clean'),
                              ('dirty', 'Dirty'),
                              ('maintenance', 'Maintenance')],
                             string="Status",
                             default='clean',
                             required=True)
    housekeeper_id = fields.Many2one('hotel.housekeeper', 'Housekeeper',
                                     required=False)
    remarks = fields.Text('Remarks')


class HotelHousekeepingStatus(models.Model):

    _name = "hotel.housekeeping.status"

    room_number_id = fields.Many2one('hotel.room.number', 'Room Number',
                                     required=True)
    room_id = fields.Many2one('hotel.room', 'Hotel Room')
    state = fields.Selection([('clean', 'Clean'),
                              ('dirty', 'Dirty'),
                              ('maintenance', 'Maintenance')],
                             string="Status",
                             default='clean',
                             required=True)
    room_status = fields.Selection([('arrived', 'Arrived'),
                                    ('available', 'Available'),
                                    ('stay_over', 'Stay Over'),
                                    ('closed', 'Closed'),
                                    ('maintenance', 'Maintenance')],
                                   string="Availability",
                                   default='available')
    housekeeper_id = fields.Many2one('hotel.housekeeper', 'Housekeeper',
                                     required=False)
    remarks = fields.Text('Remarks')

    @api.onchange('room_number_id')
    def onchange_room_number(self):
        if self.room_number_id:
            self.room_id = self.room_number_id.room_id.id or False

    @api.multi
    def write(self, vals):
        status_log_obj = self.env['hotel.housekeeping.status.log']
        if vals.get('housekeeper_id') or vals.get('state') or vals.get('remarks'):
            logs_vals = ({
                          'log_date': datetime.now(),
                          'room_number_id': self.room_number_id.id,
                          'state': vals.get('state'),
                          'housekeeper_id': vals.get('housekeeper_id'),
                          'remarks': vals.get('remarks')
                          })
            status_log_obj.sudo().create(logs_vals)
        return super(HotelHousekeepingStatus, self).write(vals)

    @api.model
    def open_housekeeping_status(self):
        view_type = 'tree'
        rooms = self.env['hotel.room.number'].search([('state', '!=', 'closed')])
        room_status_ids = []
        for room in rooms:
            rooms_status = self.search([('room_number_id', '=', room.id)])
            if not rooms_status:
                room_status = self.create({
                                            'room_number_id': room.id,
                                            'room_id': room.room_id.id,
                                           })
                room_status_ids.append(room_status.id)
            else:
                room_status_ids.extend(rooms_status.ids)
        domain = "[('id', 'in', " + str(room_status_ids) + ")]"
        value = {
            'domain': domain,
            'name': _('Housekeeping Status'),
            'view_type': 'form',
            'view_mode': view_type,
            'res_model': 'hotel.housekeeping.status',
            'type': 'ir.actions.act_window'
        }
        return value


class HotelHousekeepingActivities(models.Model):

    _name = "hotel.housekeeping.activities"
    _description = "Housekeeping Activities "

    # housekeeping_id = fields.Many2one('hotel.housekeeping', string='Reservation')
    today_date = fields.Date('Today Date')
    activity_name = fields.Many2one('hotel.housekeeping.activity',
                                    string='Housekeeping Activity')
    housekeeper = fields.Many2one('res.users', string='Housekeeper',
                                  required=True)
    clean_start_time = fields.Datetime('Clean Start Time',
                                       required=True)
    clean_end_time = fields.Datetime('Clean End Time', required=True)
    dirty = fields.Boolean('Dirty',
                           help='Checked if the housekeeping activity'
                           'results as Dirty.')
    clean = fields.Boolean('Clean', help='Checked if the housekeeping'
                           'activity results as Clean.')

    @api.constrains('clean_start_time', 'clean_end_time')
    def check_clean_start_time(self):
        '''
        This method is used to validate the clean_start_time and
        clean_end_time.
        ---------------------------------------------------------
        @param self: object pointer
        @return: raise warning depending on the validation
        '''
        if self.clean_start_time >= self.clean_end_time:
            raise ValidationError(_('Start Date Should be \
            less than the End Date!'))

    @api.model
    def default_get(self, fields):
        """
        To get default values for the object.
        @param self: The object pointer.
        @param fields: List of fields for which we want default values
        @return: A dictionary which of fields with values.
        """
        if self._context is None:
            self._context = {}
        res = super(HotelHousekeepingActivities, self).default_get(fields)
#        if self._context.get('room_id', False):
#            res.update({'room_id': self._context['room_id']})
        if self._context.get('today_date', False):
            res.update({'today_date': self._context['today_date']})
        return res
