
==========================================
Envío Masivo de Facturas por Email
==========================================

Este app permite seleccionar múltiples facturas desde la vista de lista y enviarlas por email, sin tener que realizar esta acción fatura por factura.

Requerimientos y Modificaciones
===============================

Este módulo requiere que el app account_invoice_accountant_access también esté instalado.

Una vez instalado, se podrán observar los siguientes cambios en la ventana de lista de Facturas de Clientes:

*	Una nueva columna 'Estado de Email', que muestra dos estados 'Enviado' y 'Sin Enviar'
*	Una nueva acción 'Enviar Facturas por Email'

Uso
===

Para utilizar la funcionalidad:

#. Desde Contabilidad > Ventas > Facturas de Cliente
#. Seleccione alguna de las facturas 'Validadas', pero con estado 'Sin Enviar'
#. Desde el menú 'Acción' > Enviar Facturas por Email
#. Esta acción enviará el email al cliente
#. En el chatter del registro de factura se ingresa un mensaje respecto al envío de del email

By doing this, you will create/delete the link between Journal entry and bank statement lines hence you will make corrections on the bank reconcile report which would be impossible to do through the Odoo interface.


Futuras versiones
=================

* Permitir utilizar un email distinto al principal del registro de Cliente.
