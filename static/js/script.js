/* prevents the default effect on the enter key while a text input field is focused */

window.addEventListener('keydown', function (e) {
    if (e.keyIdentifier == 'U+000A' || e.keyIdentifier == 'Enter' || e.keyCode == 13) {
        if (e.target.nodeName == 'INPUT' && e.target.type == 'text') {
            e.preventDefault();
            return false;
        }
    }
}, true);

/* client side javascript to make the preview tab functional */

const md_textarea = document.querySelector('.write #post') || document.querySelector('.edit #post');
const md_preview = document.querySelector('.write--preview') || document.querySelector('.edit--preview');

if (md_textarea && md_preview) {
    const text = md_textarea.value;
    const clean_text = DOMPurify.sanitize(text);
    md_preview.innerHTML = marked(clean_text);

    md_textarea.addEventListener('change', () => {
        const text = md_textarea.value;
        const clean_text = DOMPurify.sanitize(text);
        md_preview.innerHTML = marked(clean_text);
    });
}

const tab_button = document.querySelectorAll('.tab--link') || null;
const tabs = document.querySelectorAll('.tab--content') || null;

if (tab_button && tabs) {
    tab_button.forEach((t) => t.addEventListener('click', openTab));

    function openTab(event) {
        tab_button.forEach((t) => t.classList.remove('tab--link__focused'));
        document.querySelector('.tab--link#' + event.target.id).classList.add('tab--link__focused');
        event.target.blur();
        tabs.forEach((t) => t.classList.add('tab--hide'));
        document.querySelector('.tab--' + event.target.id.slice(0, 4)).classList.remove('tab--hide');
    }
}

/* deleting comments */

const del_button = document.querySelectorAll('.comments #del_button') || null;

if (del_button) {
    del_button.forEach((d) => d.addEventListener('click', del));

    function del (event) {
        const httpRequest = new XMLHttpRequest;
        const btn = this;
        
        httpRequest.onreadystatechange = function () {
            if (this.readyState == 4 && this.response == 201) {
                btn.parentNode.innerHTML = 'This comment was deleted';
            }
        }
       
        httpRequest.open('POST', '/comment/delete&' + this.dataset['cm']);
        httpRequest.send();
        this.blur();
    }
}