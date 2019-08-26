from odoo import http, models, fields, api, _, tools
from ast import literal_eval

class CrmLead2OpportunityPartner(models.TransientModel):
    _inherit = "crm.lead2opportunity.partner"

    main_id_category_id = fields.Many2one('res.partner.id_category',
                                          string="Main Identification Category",
                                          translate=True)
    main_id_number = fields.Char(string="CUIT",translate=True)
    fantasy_name = fields.Char(string="Fantasy Name",translate=True)
    email = fields.Char()

    @api.multi
    def action_apply(self):
        res = super(CrmLead2OpportunityPartner, self).action_apply()
        lead = self.env['crm.lead'].browse(int(res['res_id']))
        if self.main_id_category_id.afip_code == 80:
            partner_vals = lead.partner_id.get_data_from_padron_afip(self.main_id_number.replace('-',''))
            lead.partner_id.write({'afip_responsability_type_id': int(partner_vals['afip_responsability_type_id']),
                                   'actividades_padron': [(6, False, partner_vals['actividades_padron'])],
                                   'monotributo_padron': partner_vals['monotributo_padron'],
                                   'empleador_padron': partner_vals['empleador_padron'],
                                   'actividad_monotributo_padron': partner_vals['actividad_monotributo_padron'],
                                   'impuestos_padron': [(6, False, partner_vals['impuestos_padron'])],
                                   'integrante_soc_padron': partner_vals['integrante_soc_padron'],
                                   'last_update_padron': partner_vals['last_update_padron'],
                                   'imp_ganancias_padron': partner_vals['imp_ganancias_padron'],
                                   'name': partner_vals['name'],
                                   'zip': partner_vals['zip'],
                                   'street': partner_vals['street'],
                                   'estado_padron': partner_vals['estado_padron'],
                                   'state_id': int(partner_vals['state_id']),
                                   'imp_iva_padron': partner_vals['imp_iva_padron']})
            pais = self.env['res.country.state'].browse(int(partner_vals['state_id'])).country_id
            lead.partner_id.country_id = pais.id
        lead.partner_id.main_id_number = self.main_id_number.replace('-', '')
        if self.email:
            lead.partner_id.email = self.email
        if self.fantasy_name:
            lead.partner_id.ref = self.fantasy_name
        lead.partner_id.main_id_category_id = self.main_id_category_id.id
        return res

