/* vote-system */
function human_format(num, digits=2) {
    var si = [{
            value: 1,
            symbol: ""
        },
        {
            value: 1E3,
            symbol: "k"
        },
        {
            value: 1E6,
            symbol: "M"
        },
        {
            value: 1E9,
            symbol: "G"
        },
        {
            value: 1E12,
            symbol: "T"
        },
        {
            value: 1E15,
            symbol: "P"
        },
        {
            value: 1E18,
            symbol: "E"
        }
    ];
    var rx = /\.0+$|(\.[0-9]*[1-9])0+$/;
    var i;
    for (i = si.length - 1; i > 0; i--) {
        if (num >= si[i].value) {
            break;
        }
    }
    return (num / si[i].value).toFixed(digits).replace(rx, "$1") + si[i].symbol;
}

const upvote_btns = document.querySelectorAll('.comments--comment__btn--up');
const downvote_btns = document.querySelectorAll('.comments--comment__btn--down');
const reply_upvote_btns = document.querySelectorAll('.comments--reply__btn--up');
const reply_downvote_btns = document.querySelectorAll('.comments--reply__btn--down');

if (upvote_btns && downvote_btns) {
    upvote_btns.forEach((u) => u.addEventListener('click', upvote));
    reply_upvote_btns.forEach((u) => u.addEventListener('click', upvote));
    downvote_btns.forEach((d) => d.addEventListener('click', downvote));
    reply_downvote_btns.forEach((d) => d.addEventListener('click', downvote));

    function makeRequest(btn, type) {
        const httpRequest = new XMLHttpRequest;

        const currVotect = btn.parentNode.querySelector('.comments--comment__votect') || btn.parentNode.querySelector('.comments--reply__votect');
        let currVote = parseInt(currVotect.dataset['vote']);

        httpRequest.onreadystatechange = function () {
            if (this.readyState == 4 && this.response == 200) {
                btn.classList.add('active');

                currVote += (btn.classList[1].includes('--up') ? 1 : -1);
                currVotect.dataset['vote'] = currVote;
                currVotect.innerHTML = (currVote > 0 ? '+' : '') + human_format(currVote);
            } else if (this.readyState == 4 && this.response == 201) {
                btn.classList.remove('active');

                currVote += (btn.classList[1].includes('--up') ? -1 : 1);
                currVotect.dataset['vote'] = currVote;
                currVotect.innerHTML = (currVote > 0 ? '+' : '') + human_format(currVote);
            } else if (this.readyState == 4 && this.response == 202) {
                btn.parentNode.querySelectorAll('.' + btn.classList[0]).forEach((btn) => btn.classList.remove('active'));
                btn.classList.add('active');

                currVote += (btn.classList[1].includes('--up') ? 2 : -2);
                currVotect.dataset['vote'] = currVote;
                currVotect.innerHTML = (currVote > 0 ? '+' : '') + human_format(currVote);
            } else if (this.readyState == 4) {
                window.location.replace(this.responseURL);
            }
        }

        httpRequest.open('post', '/comment/' + type + 'vote&' + btn.dataset['cm']);
        httpRequest.send();
        btn.blur();
    }

    function upvote() {
        const btn = this;
        makeRequest(btn, 'up');
    }

    function downvote() {
        const btn = this;
        makeRequest(btn, 'down');
    }
}