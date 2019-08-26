odoo.define('payment_mercadopago.mercadopago',function(require){
    "use_strict";

//    var Model = require('web.Model');

    Mercadopago.setPublishableKey("TEST-5757d909-809a-439c-b6ca-ef6d90c77a50");
	Mercadopago.getIdentificationTypes();

    function addEvent(el, eventName, handler){
    if (el.addEventListener) {
    	console.log("12234455666",el,el.addEventListener, handler);
           el.addEventListener(eventName, handler);
	} else {
		console.log("234322223",el);
        el.attachEvent('on' + eventName, function(){
          handler.call(el);
        });
    	}
	};

    function getBin() {
        var ccNumber = document.querySelector('input[name="cc_number"]');
        return ccNumber.value.replace(/[ .-]/g, '').slice(0, 6);
    };

    function guessingPaymentMethod(event) {
        var bin = getBin();
        console.log("insideguessing payent method function");
        if (event.type == "keyup") {
            if (bin.length >= 6) {
                Mercadopago.getPaymentMethod({
                    "bin": bin
                }, setPaymentMethodInfo);
            }
        } else {
            setTimeout(function() {
                if (bin.length >= 6) {
                    Mercadopago.getPaymentMethod({
                        "bin": bin
                    }, setPaymentMethodInfo);
                }
            }, 100);
        }
    };


    function setPaymentMethodInfo(status, response) {
        if (status == 200) {
            // console.log('------status------',status)
            // do somethings ex: show logo of the payment method
            var form = document.querySelector('.o_payment_form');

            if (document.querySelector("input[name=paymentMethodId]") == null) {
                var paymentMethod = document.createElement('input');
                paymentMethod.setAttribute('name', "paymentMethodId");
                paymentMethod.setAttribute('type', "hidden");
                paymentMethod.setAttribute('value', response[0].id);

                form.appendChild(paymentMethod);
            } else {
                document.querySelector("input[name=paymentMethodId]").value = response[0].id;
            }
        }
    };


//    function sdkResponseHandler(status, response) {
////    var self = this;
//    if (status != 200 && status != 201) {
//        alert("verify filled data");
//    }else{
//
//        var ajax = require('web.ajax');
//
//        var form = document.querySelector('.o_payment_form');
//
//        var card = document.createElement('input');
//        card.setAttribute('name',"token");
//        card.setAttribute('type',"hidden");
//        card.setAttribute('value',response.id);
//        form.appendChild(card);
//
//        doSubmit=true;
//        console.log("------response--------",response);
//
////        vals.update(response)
////        console.log("------vals--------",vals);
//
//
//
//
//        $('.response111').val(response['id']);
//
//        vals = {
//                'customer_email': $('#email').val(),
//                'cc_number': $('#cardNumber').val(),
//                'cc_brand': $('#securityCode').val(),
//                'cc_holder_name': $('#cardExpirationMonth').val(),
//                'cc_expiry': $('#cardExpirationYear').val(),
//                'response': $('#response111').val(),
////                'cc_cvc': $('.mercadopago_cc_cvc').val(),
////                'docType': $('.mercadopago_docType').val(),
////                'docNumber': $('.mercadopago_docNumber').val(),
//            }
//
////        document.getElementById("response111").setAttribute('value','FUUUUUUKKKKKKK');
//        console.log("------sdkHandler-vals-------",vals['response'])
////        alert('33333333333333333');
////        document.getElementById("response111").value = response['id'];
//
////        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
////            model:  'payment.acquirer',
////            method: 'get_card_token',
////            args: [],
////            kwargs: {
////                data: response
////            },
//////            data:{}
////        });
////        new Model("payment.acquirer").call("mercadopago_s2s_form_process",[{
////							'type': 'message',
////							'date': new Date(),
////							'description': 'FUUUUUUUUUUUUCK'
////						}])
//
////        form.submit();
//
////        return response
//
//
//        }
//    };

    doSubmit = false;

    function doPay(event, vals){
        console.log("e>>>>>>>>>>>>>",event)
        event.preventDefault();
        return false;

//        if(!doSubmit){
//            var $form = document.querySelector('.o_payment_form');
//            console.log('----$form------',$form);
//            console.log('----vals------',vals);
//    //        return false;
//    //        alert('222222222222');
//            Mercadopago.createToken($form, sdkResponseHandler); // The function "sdkResponseHandler" is defined below
//            return false;
//        }
    };


//


    $(document).ready(function (){
        console.log( "ready!",document.querySelector('form[class="o_payment_form"]' ));
        addEvent(document.querySelector('input[data-checkout="cardNumber"]'), 'keyup', guessingPaymentMethod);
        addEvent(document.querySelector('input[data-checkout="cardNumber"]'), 'change', guessingPaymentMethod);
//        addEvent(document.getElementById('o_payment_form_pay'),'click',doPay);

//        document.querySelector('form[class="o_payment_form"]').onsubmit = function(){doPay(event)}



        $('.o_payment_form').submit( function(e) {
//        $('#o_payment_form_pay').on('click', function(e){
            console.log('Form has been clicked!')
            e.preventDefault();
            var token_id = ""
        // do your things ...

            function sdkResponseHandler(status, response) {
        //    var self = this;
            if (status != 200 && status != 201) {
                alert("verify filled data");
            }else{

                var ajax = require('web.ajax');

                var form = document.querySelector('.o_payment_form');

                var card = document.createElement('input');
                card.setAttribute('name',"token");
                card.setAttribute('type',"hidden");
                card.setAttribute('value',response.id);
                form.appendChild(card);

                doSubmit=true;
                console.log("------response--------",response);
                token_id = response['id']
        //        vals.update(response)
                console.log("------token_id--------",token_id);




                $('.response111').val(response['id']);

                vals = {
                        'customer_email': $('#email').val(),
                        'cc_number': $('#cardNumber').val(),
                        'cc_brand': $('#securityCode').val(),
                        'cc_holder_name': $('#cardExpirationMonth').val(),
                        'cc_expiry': $('#cardExpirationYear').val(),
                        'response': $('#response111').val(),
        //                'cc_cvc': $('.mercadopago_cc_cvc').val(),
        //                'docType': $('.mercadopago_docType').val(),
        //                'docNumber': $('.mercadopago_docNumber').val(),
                    }

        //        document.getElementById("response111").setAttribute('value','FUUUUUUKKKKKKK');
                console.log("------sdkHandler-vals-------",vals['response'])
        //        alert('33333333333333333');
        //        document.getElementById("response111").value = response['id'];

        //        return ajax.jsonRpc('/web/dataset/call_kw', 'call', {
        //            model:  'payment.acquirer',
        //            method: 'get_card_token',
        //            args: [],
        //            kwargs: {
        //                data: response
        //            },
        ////            data:{}
        //        });
        //        new Model("payment.acquirer").call("mercadopago_s2s_form_process",[{
        //							'type': 'message',
        //							'date': new Date(),
        //							'description': 'FUUUUUUUUUUUUCK'
        //						}])

        //        form.submit();

        //        return response


                }
            };


        // and when you done:

            var $form = document.querySelector('.o_payment_form');
            console.log('----$form------',$form);
//            console.log('----vals------',vals);
    //        return false;
    //        alert('222222222222');
            Mercadopago.createToken($form, sdkResponseHandler); // The function "sdkResponseHandler" is defined below
    //        return false;

            alert('222222222222');
            $('.o_payment_form').submit();
    });





//           $('#o_payment_form_pay').on('click', function(ev){
//            vals = {
//                'customer_email': $('.mercadopago_customer_email').val(),
//                'cc_number': $('.mercadopago_cc_number').val(),
//                'cc_brand': $('.mercadopago_cc_brand').val(),
//                'cc_holder_name': $('.mercadopago_cc_holder_name').val(),
//                'cc_expiry': $('.mercadopago_cc_expiry').val(),
//                'cc_expiry': $('.mercadopago_cc_expiry').val(),
//                'cc_cvc': $('.mercadopago_cc_cvc').val(),
//                'docType': $('.mercadopago_docType').val(),
//                'docNumber': $('.mercadopago_docNumber').val(),
//            }
////            var access_token = Mercadopago.setPublishableKey("TEST-5757d909-809a-439c-b6ca-ef6d90c77a50");
////            console.log( "------------access_token----------------", access_token);
//
//            doPay(ev, vals)
//            console.log( "----------------------------", sdkResponseHandler);
//
////            alert('222222222222')
////            return false;
//        });


    });



})