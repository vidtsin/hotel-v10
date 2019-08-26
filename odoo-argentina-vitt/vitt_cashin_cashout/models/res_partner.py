from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError

class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_id = fields.Many2one('hr.employee', string="Employee")
