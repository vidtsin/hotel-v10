# coding=utf-8
import logging
import pprint
import werkzeug
import urlparse

from odoo import http, _
from odoo.http import request
import odoo.exceptions
from odoo.exceptions import UserError
from werkzeug import urls, utils
import json

_logger = logging.getLogger(__name__)

from ..models.mercadopago_request import MecradoPagoPayment
from odoo.addons.website_sale.controllers.main import WebsiteSale

# class WebsiteSale(WebsiteSale):
#
#     @http.route('/shop/payment/token', type='http', auth='public', website=True)
#     def payment_token(self, pm_id=None, **kwargs):
#         """ Method that handles payment using saved tokens
#
#         :param int pm_id: id of the payment.token that we want to use to pay.
#         """
#         print("-------testing for flow in payment_token--------")
#         print("--------payment_token-------",kwargs)
#         order = request.website.sale_get_order()
#         print("----order------",order)
#         if kwargs.get('payment_method') == 'cash' or kwargs.get('payment_method') == 'bank_transfer' and kwargs.get('payment_type_bank'):
#             tx = request.env['payment.transaction'].sudo().search([('sale_order_id' , '=', order.id)])
#             print("------transaction : ",tx)
#             request.session['sale_transaction_id'] = tx.id
#             return request.redirect('/shop/payment/validate?success=True')
#         else:
#             # do not crash if the user has already paid and try to pay again
#             if not order:
#                 return request.redirect('/shop/?error=no_order')
#
#             assert order.partner_id.id != request.website.partner_id.id
#
#             try:
#                 pm_id = int(pm_id)
#             except ValueError:
#                 return request.redirect('/shop/?error=invalid_token_id')
#
#             # We retrieve the token the user want to use to pay
#             token = request.env['payment.token'].sudo().browse(pm_id)
#             print("----token----",token)
#             if not token:
#                 return request.redirect('/shop/?error=token_not_found')
#
#             # we retrieve an existing transaction (if it exists obviously)
#             tx = request.website.sale_get_transaction() or request.env['payment.transaction'].sudo()
#             print("---------tx----------",tx)
#             # we check if the transaction is Ok, if not then we create it
#             tx = tx.sudo()._check_or_create_sale_tx(order, token.acquirer_id, payment_token=token, tx_type='server2server')
#             # we set the transaction id into the session (so `sale_get_transaction` can retrieve it )
#             request.session['sale_transaction_id'] = tx.id
#             # we proceed the s2s payment
#             print("--------33333333333-----tx from website sale--------", tx)
#             res = {k: v for k, v in kwargs.items() if "cc_cvc" in k and v is not ''}
#             if res:
#                 print("-------------tx from website sale--------", res)
#                 tx = tx.with_context(cc_cvc=list(res.values())[0])
#             res = tx.confirm_sale_token()
#             print("---------res in payment_token---------",res)
#             if res == 'pay_sale_tx_fail' and tx.acquirer_id.provider == 'mercadopago':
#                 return request.redirect("/mercadopago/reject_payment"   )
#             if res == 'pay_sale_tx_state' and tx.acquirer_id.provider == 'mercadopago':
#                 print("trying to redirect to payment failed page.")
#                 msg = request.session.get('state_message')
#                 request.session['state_message'] = False
#                 return request.redirect("/mercadopago/reject_payment?state_msg="+msg)
#             # we then redirect to the page that validates the payment by giving it error if there's one
#             if res is not True:
#                 # print("We got some issues here. res is False already. Deal with it somehow")
#                 return request.redirect('/shop/payment/validate?success=False&error=%s' % res)
#             return request.redirect('/shop/payment/validate?success=True')
#
#     @http.route(['/shop/confirmation'], type='http', auth="public", website=True)
#     def payment_confirmation(self, **post):
#         """ End of checkout process controller. Confirmation is basically seing
#         the status of a sale.order. State at this point :
#
#          - should not have any context / session info: clean them
#          - take a sale.order id, because we request a sale.order and are not
#            session dependant anymore
#         """
#         print("----------post-------",post)
#         print("inside confirm mathod.")
#         sale_order_id = request.session.get('sale_last_order_id')
#         print("sale order id is : ", sale_order_id)
#         if sale_order_id:
#             order = request.env['sale.order'].sudo().browse(sale_order_id)
#             tx = request.env['payment.transaction'].sudo().search([('sale_order_id', '=', order.id)])
#             # print("---------transction with msg : ",tx, tx.state_message)
#             return request.render("website_sale.confirmation", {'order': order, 'msg' : tx.state_message})
#         else:
#             return request.redirect('/shop')


class MercadoPagoController(http.Controller):

    @http.route(['/mercadopago/shop/payment/validate'], type='http', auth='public')
    def mercadopago_form_feedback(self, **post):
        # print("Inside Mercadopago Payment Transaction method")
        # print("-----request--------",request.session)
        # print("-----------post----------",post)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        r_url = "/shop/payment/validate"
        acquirer = request.env['payment.acquirer'].sudo()
        # print("acquirer------------",acquirer)
        if request.session.get('pref_id') == post.get('preference_id'):
            if not request.session.get('sale_transaction_id') or request.session.get('website_payment_tx_id', False):
                Transaction = request.env['payment.transaction'].sudo()
                acquirer_id = acquirer.search([('provider', '=', 'mercadopago')]).id
                order = request.env['sale.order'].sudo().search([('id', '=', request.session.get('sale_order_id'))])
                tx_values = {'acquirer_id': acquirer_id,
                             'type': 'form',
                             'amount': order.amount_total,
                             'currency_id': order.pricelist_id.currency_id.id,
                             'partner_id': order.partner_id.id,
                             'partner_country_id': order.partner_id.country_id.id,
                             'reference': Transaction.get_next_reference(order.name),
                             'sale_order_id': order.id,
                }
                tx = Transaction.create(tx_values)
                request.session['sale_transaction_id'] = tx.id
            else :
                tx = request.env['payment.transaction'].sudo().browse(
                    int(request.session.get('sale_transaction_id') or request.session.get('website_payment_tx_id', False)))
            # print("-------tx-----------",tx)
            post.update({'sale_transaction_id' : tx.id})
            request.env['payment.transaction'].sudo().form_feedback(post, 'mercadopago')
        # 2/0
        # print "-----------url to redirect : ",base_url + r_url
        return request.render('payment_mercadopago.payment_mercadopago_redirect',
                              {'return_url': '%s' % urlparse.urljoin(base_url, r_url)})

    @http.route(['/payment/mercadopago/deposit'],type='json', auth='public')
    def mercadopago_payment_deposit(self, **kwargs):
        # print("-----------post",kwargs)
        # print("------request",request, request.session)
        acquirer_id = request.env['payment.acquirer'].search([('id', '=', kwargs.get('acquirer_id'))])
        order = request.env['sale.order'].search([('id', '=', request.session.get('sale_order_id'))])
        mp = MecradoPagoPayment(acquirer_id)
        # 2/0
        # print("mp---------",mp)
        if kwargs.get('payment_method'):
            tx = request.env['payment.transaction'].sudo().browse(
                int(request.session.get('sale_transaction_id') or request.session.get('website_payment_tx_id', False)))
            # print("--------tx from mercadopago payment deposit------",tx, order)
            if not tx:
                # print("Create it please!")
                tx = tx.sudo()._check_or_create_sale_tx(order, acquirer_id, payment_token=False,
                                                        tx_type='form')
            else:
                tx = tx
            # 2/0
            kwargs.update({'sale_transaction_id' : tx.id})
            payment_resp = mp.marcadopago_payment_manual(tx, kwargs)
            # print("payment_resp----------",payment_resp)
            # print("transaction : ",tx)
            if payment_resp:
                if tx and payment_resp.get('transaction_details').get('external_resource_url'):
                    # print("hellooooo... gotcha!!")
                    # print("external resource", payment_resp.get('transaction_details').get('external_resource_url'))
                    tx.write({'state_message': payment_resp.get('transaction_details').get('external_resource_url')})
                    # print("state msg", tx.state_message)
                kwargs.update({'id' : payment_resp.get('id'),
                               'external_resource_url' : payment_resp.get('external_resource_url'),
                               'mp_payment_type_id' : payment_resp.get('payment_type_id'),
                               'status' : payment_resp.get('status'),
                               'status_detail' : payment_resp.get('status_detail'),
                               }
                              )
                request.env['payment.transaction'].sudo().form_feedback(kwargs, 'mercadopago')
                # tx.sale_order_id.with_context(send_email=True).action_confirm()
                # tx._generate_and_pay_invoice()
                return {"result": True, "id" : acquirer_id.id, "3d_secure" : False}
            else:
                return request.render("payment_mercadopago.reject_payment_template")
        return utils.redirect('/shop')

    @http.route(['/payment/mercadopago/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def mercadopago_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        # print("------mercadopago_s2s_create_json_3ds-----",kwargs)
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        if not token:
            res = {'result': False, }
            return res

        res = {'result': True,
               'id': token.id,
               'short_name': token.short_name,
               '3d_secure': False,
               'verified': False, }

        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified
        return res

    # @http.route(['/payment/mercadopago/s2s/create'], type='http', auth='public')
    # def mercadopago_s2s_create(self, **post):
    #     acquirer_id = int(post.get('acquirer_id'))
    #     acquirer = request.env['payment.acquirer'].browse(acquirer_id)
    #     acquirer.s2s_process(post)
    #     return utils.redirect(post.get('return_url', '/'))

    @http.route(['/mercadopago/reject_payment'], type='http', auth='public', website=True)
    def reject_payment(self, **data):
        # print("------controller calling--------",data,request.session.get('state_message'))
        msg = data.get('state_msg')
        return request.render("payment_mercadopago.reject_payment_template", {'msg':msg})

    @http.route(['/ipn/notification'], type='json', auth='public')
    def mercadopago_ipn_notification(self, **kwargs):
        # print("*************", request.jsonrequest, type(request.jsonrequest))
        kwargs =    request.jsonrequest
        # print("----------request has been received with arguements : ",kwargs)
        acquirer_id = request.env['payment.acquirer'].sudo().search([('provider', '=', 'mercadopago')], limit=1)
        mp = MecradoPagoPayment(acquirer_id)
        # print("---------",acquirer_id, mp)
        if acquirer_id.mercadopago_use_ipn:
            if kwargs.get('id'):
                p_id = kwargs.get('id')
            elif kwargs.get('resource'):
                p_id = kwargs.get('resource').split('/')[-1]
            # print("-------p_id-------",p_id)
            if kwargs and kwargs.get('topic') and p_id:
                response = mp.get_payment_update(p_id)
                if response.get('status') in (200, 201) and response.get('data'):
                    _logger.info('Payment status has been changed for MercadoPago Payment of Sale Order : %s to %s, now changing payment status in Odoo.', response.get('data').get('description'), response.get('data').get('status'))
                    tx = request.env['payment.transaction'].sudo().search([('acquirer_reference', '=', response.get('data').get('id'))])
                    if not tx:
                        raise odoo.exceptions.MissingError('Transaction does not exist or has been deleted for MercadoPago Payment reference : %s'% response.get('data').get('id'))

                    status = "pending" if response.get('data').get('status') in ("in_process", "pending") else response.get('data').get('status')
                    if tx.status == status:
                        _logger.info('Payment status is already in same state.')
                    tx.write({'state' : status})
                    if response.get('data').get('status') == "approved" and tx.state in ('authorized', 'done'):
                        _logger.info("Payment has been done, now confirming Sale Order as well paying invoice.")
                        tx.sale_order_id.with_context(send_email=True).action_confirm()
                        tx._generate_and_pay_invoice()

            topic = kwargs["topic"]
            merchant_order_info = None

            if topic == "payment":
                payment_info = mp.get("/v1/payments/" + kwargs.get("id"))
                merchant_order_info = mp.get("/merchant_orders/" + payment_info.get("response").get("order").get("id"))
            elif topic == "merchant_order":
                merchant_order_info = mp.get("/merchant_orders/" + kwargs.get("id"))

            if merchant_order_info == None:
                raise ValueError("Error  obtaining  the  merchant_order")

            if merchant_order_info["status"] == 200:
                return {"payment": merchant_order_info["response"]["payments"],
                    "shipment": merchant_order_info["response"]["shipments"]}
            else:
                return False
        else:
            # print("Inside else")
            return False
