# -*- coding: utf-8 -*-
{
    'name': "Moogah Setup Localization Modules", 

    'summary': """Instalacion automatica de modulos para la localizacion Argentina""",

    'description': """
        Instala de forma automática todos los siguientes módulos: Campos de localización, Cheques, Pagos en Grupos, Tablas impositivas, Retenciones, Facturación Electrónica y otros.
        """,

    'author': "Moogah",
    'website': "http://www.moogah.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '10.0.1.1',

    # any module necessary for this one to work correctly
    'depends': [
        'l10n_ar_account',
        'account_check',
        'account_payment_group',
        'account_check_deposit',
        'l10n_ar_bank',
        'l10n_ar_afipws_fe',
        'l10n_ar_account_withholding',
        'vitt_arg_einvoice_format',
    #    'vitt_afip_invoice_barcode',
        'account_invoice_tax_wizard',
        'account_tax_report',
        'vitt_sales_reports',
        'vitt_acc_paym_print',
        'vitt_stock_report',
        'vitt_cashin_cashout',
    # Is not finished yet   'vitt_arg_check_history_reports',
        'vitt_CAE_recover',
        'vitt_per_wh_setting',
        'vitt_report_settings',
        'vitt_tax_exceptions',
        'vitt_lang_no_format'        
     ],
    # always loaded
    # only loaded in demonstration mode
    'demo': [],
    'application': True,
}