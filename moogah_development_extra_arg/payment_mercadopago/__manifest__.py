# coding=utf-8
{
    'name': 'MercadoPago Payment Acquirer',
    'category': 'Accounting',
    'author' : 'Moogah',
    'website' : 'www.techultrasolutions.com',
    'summary': 'Payment Acquirer: MercadoPago Integration for Argentina',
    'version': '10.0.1.4.1',
    'description': """MercadoPago Payment Acquirer""",
    'depends': ['payment', 'website', 'website_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_views.xml',
        'views/payment_mecradopago_templates.xml',
        'views/res_partner_modifications.xml',
        'data/payment_acquirer_data.xml',
        'data/ir_cron_transaction.xml',
    ],
    'installable': True,
    "price": 360,
    "currency": 'USD',
}
