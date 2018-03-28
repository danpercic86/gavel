$(document).ready(function(){

    // manage team selection and unlock vote button
    $('.label-team').click(function(){
        $('.label-team').removeClass('active');
        $(this).addClass('active');
        $('.button-vote').show();
    });

    // implement tabs
    $('#myTab a').on('click', function (e) {
        e.preventDefault()
        $(this).tab('show');
    })
});