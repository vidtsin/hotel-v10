from odoo import api, fields, models, _


class PosOrder(models.Model):
    _inherit = 'pos.order'

    # -------------Overwritten-------------
    @api.multi
    def refund2(self):
        """Create a copy of order  for refund order"""
        PosOrder = self.env['pos.order']
        current_session = self.env['pos.session'].search([('state', '!=', 'closed'), ('user_id', '=', self.env.uid)], limit=1)
        if not current_session:
            raise UserError(_('To return product(s), you need to open a session that will be used to register the refund.'))
        for order in self:
            clone = order.copy({
                # ot used, name forced by create
                'name': order.name + _(' REFUND'),
                'session_id': current_session.id,
                'date_order': fields.Datetime.now(),
                'pos_reference': order.pos_reference,
            })
            PosOrder += clone

        for clone in PosOrder:
            for order_line in clone.lines:
                order_line.write({'qty': -order_line.qty})

            # NEW
            data = dict()
            for pay in order.statement_ids:
                data.update({'amount': pay.amount * -1, 'payment_date': pay.date, 'journal': pay.journal_id.id})
                clone.add_payment(data)
            if clone.test_paid():
                clone.action_pos_order_paid()
            # NEW

        return {
            'name': _('Return Products'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'pos.order',
            'res_id': PosOrder.ids[0],
            'view_id': False,
            'context': self.env.context,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }
