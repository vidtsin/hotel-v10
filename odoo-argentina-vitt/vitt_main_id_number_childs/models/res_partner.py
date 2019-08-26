from odoo import http, models, fields, api, _, tools

class ResPartner(models.Model):
    _inherit = 'res.partner'

    def create_id_numbers(self):
        root_partner = self.env['res.partner'].search([('child_ids', 'ilike', self.id)])
        if root_partner.main_id_number and root_partner.main_id_category_id:
            self.main_id_category_id = root_partner.main_id_category_id
            self.afip_responsability_type_id = root_partner.afip_responsability_type_id
            self.id_numbers.create({
                'partner_id': self.id,
                'category_id': self.main_id_category_id.id,
                'name': root_partner.main_id_number
            })

    @api.model
    def create(self,vals):
        res = super(ResPartner, self).create(vals)
        res.create_id_numbers()
        return res

    def cron_create_id_numbers(self):
        parents = self.env['res.partner'].search([('child_ids', '!=', False)])
        for parent in parents:
            for child in parent.child_ids:
                if not child.main_id_number:
                    child.create_id_numbers()
