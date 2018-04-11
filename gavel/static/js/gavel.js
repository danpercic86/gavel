$(document).ready(function(){


    // implement tabs
    $('#myTab a').on('click', function (e) {
        e.preventDefault()
        $(this).tab('show');
    });


    if($('body').hasClass('judge-view')) {
        var timePerProject = 5;
        var maxTimePerProject = 10;
        var endJuryTime = new Date(Date.UTC(2018, 4, 11, 23, 0, 0));

        // manage team selection and unlock vote button
        $('.label-team').click(function () {
            $('.label-team').removeClass('active');
            $(this).addClass('active');
            $('.button-vote').show();

            window.scrollTo(0,document.body.scrollHeight);

        });


        $('.btn-overlay').on('click', function (e) {
            e.preventDefault();

            var role = $(this).data('role');

            if (role == 'vote-start') {
                var date = new Date();
                var tempData = {
                    'id': currentProject,
                    'timeStart': date.getTime()
                };
                setCookie('projectCounter', JSON.stringify(tempData));
                $('.overlay').hide();

                updateTimer(getCookie('projectCounter', 'timeStart'), '#time-spent');
            }
        });


        if (getCookie('projectCounter', 'id') == currentProject) {
            $('.overlay').hide();
            updateTimer(getCookie('projectCounter', 'timeStart'), '#time-spent');
        }


        function setCookie(key, value) {
            var expires = new Date();
            expires.setTime(expires.getTime() + (1 * 24 * 60 * 60 * 1000));
            document.cookie = key + '=' + value + ';expires=' + expires.toUTCString();
        }

        function getCookie(set, key) {
            var keyValue = document.cookie.match('(^|;) ?' + set + '=([^;]*)(;|$)');
            var rawValue = keyValue ? keyValue[2] : null;
            return JSON.parse(rawValue)[key];
        }

        function updateTimer(start, container) {
            var startDateTime = new Date(start);
            var startStamp = startDateTime.getTime();

            var newDate = new Date();
            var newStamp = newDate.getTime();

            var timer;

            function updateClock() {
                newDate = new Date();
                newStamp = newDate.getTime();
                var diff = Math.round((newStamp - startStamp) / 1000);

                var d = Math.floor(diff / (24 * 60 * 60));
                diff = diff - (d * 24 * 60 * 60);
                var h = Math.floor(diff / (60 * 60));
                diff = diff - (h * 60 * 60);
                var m = Math.floor(diff / (60));
                diff = diff - (m * 60);
                var s = diff;

                if (m > timePerProject) {
                    $(container).parent('div').addClass('alert-blink');

                    if (m > maxTimePerProject) {
                        $('body').addClass('alert-blink');
                    }
                }

                $(container).html(m + " m : " + s + " s");
            }

            setInterval(updateClock, 1000);
        }

        function updateTimeLeft() {

            var newDate = new Date();
            var newStamp = newDate.getTime();

            function calculateTimeLeft() {
                newDate = new Date();
                newStamp = newDate.getTime();
                var diff = Math.round((endJuryTime - newStamp) / 1000);

                var d = Math.floor(diff / (24 * 60 * 60));
                diff = diff - (d * 24 * 60 * 60);
                var h = Math.floor(diff / (60 * 60));
                diff = diff - (h * 60 * 60);
                var m = Math.floor(diff / (60));
                diff = diff - (m * 60);
                var s = diff;

                $('#time-left').html(h + " h : " + s + " m");
            }

            setInterval(calculateTimeLeft, 1000);
        }

        updateTimeLeft();
    }
});