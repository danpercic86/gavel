function updateTimer(start, container) {
    const startDateTime = new Date(start);
    const startStamp = startDateTime.getTime();

    function updateClock() {
        const newStamp = new Date().getTime();
        const diff = Math.round((newStamp - startStamp) / 1000);
        const {m, s} = getTime(diff);

        if (m >= timePerProject) {
            $(container).parent('div').addClass('alert-blink');

            if (m >= maxTimePerProject) {
                $('body').addClass('alert-blink');
            }
        }

        $(container).html(m + " m : " + s + " s");
    }

    setInterval(updateClock, 1000);
}

function getTime(diff) {
    const d = Math.floor(diff / (24 * 60 * 60));
    diff = diff - (d * 24 * 60 * 60);
    const h = Math.floor(diff / (60 * 60));
    diff = diff - (h * 60 * 60);
    const m = Math.floor(diff / (60));
    const s = diff % 60;
    return {h, m, s};
}

function calculateTimeLeft() {
    const newStamp = new Date().getTime();

    let diff = Math.round((endJuryTime - newStamp) / 1000);
    const {h, m} = getTime(diff);

    $('#time-left').html(h + " h : " + m + " m");
}

function setCookie(key, value) {
    const expires = new Date();
    expires.setTime(expires.getTime() + (1 * 24 * 60 * 60 * 1000));
    document.cookie = key + '=' + value + ';expires=' + expires.toUTCString();
}

function getCookie(set, key) {
    const keyValue = document.cookie.match('(^|;) ?' + set + '=([^;]*)(;|$)');
    const rawValue = keyValue ? keyValue[2] : null;
    return (JSON.parse(rawValue) || {})[key];
}


$(document).ready(function () {
    // manage team selection and unlock vote button
    $('.label-team').click(function () {
        $('.label-team').removeClass('active');
        $(this).addClass('active');
        $('.button-vote').show();

        window.scrollTo(0, document.body.scrollHeight);

    });

    if (getCookie('projectCounter', 'id') === currentProject) {
        $('.overlay').hide();
        updateTimer(getCookie('projectCounter', 'timeStart'), '#time-spent');
    } else {
        const tempData = {'id': currentProject, 'timeStart': new Date().getTime()};
        setCookie('projectCounter', JSON.stringify(tempData));
        $('.overlay').hide();
        updateTimer(getCookie('projectCounter', 'timeStart'), '#time-spent');
    }


    setInterval(calculateTimeLeft, 1000);
});
