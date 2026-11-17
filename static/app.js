const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

let shop = {};
let cart = {};       // { id товара: количество }
let category = '';

const $ = (id) => document.getElementById(id);
const money = (n) => n.toLocaleString('ru-RU') + ' ' + shop.currency;
const findProduct = (id) => shop.products.find((p) => p.id == id);

async function load() {
    shop = await fetch('/api/shop').then((r) => r.json());

    document.title = shop.name;
    document.documentElement.style.setProperty('--accent', shop.accent);
    $('name').textContent = shop.name;
    $('description').textContent = shop.description;

    // Имя из Telegram в форму
    $('form').elements.name.value =tg.initDataUnsafe.user?.first_name || '';

    category = shop.products[0].category;
    render();
}

//Меню 

function render() {
    const categories = [...new Set(shop.products.map((p) => p.category))];
    $('tabs').innerHTML = categories.map((c) =>
        `<button class="tab ${c === category ? 'active' : ''}" onclick="selectCategory('${c}')">${c}</button>`
    ).join('');

    $('grid').innerHTML = shop.products
        .filter((p) => p.category === category)
        .map((p) => `
            <div class="card">
                <img src="/static/images/${p.image}" alt="${p.name}">
                <h3>${p.name}</h3>
                <p>${p.description}</p>
                <div class="card-bottom">
                    <span>${money(p.price)}</span>
                    ${cart[p.id] ? stepper(p.id) : `<button class="add" onclick="add(${p.id})">+</button>`}
                </div>
            </div>`)
        .join('');

    const count = Object.values(cart).reduce((a, b) => a + b, 0);
    $('cartButton').hidden = count === 0;
    $('cartButton').textContent = `Корзина · ${count} шт · ${money(total())}`;
}

function stepper(id) {
    return `<div class="stepper">
        <button onclick="remove(${id})">−</button>
        <span>${cart[id]}</span>
        <button onclick="add(${id})">+</button>
    </div>`;
}

function selectCategory(c) {
    category = c;
    render();
}

// Корзина 

function total() {
    return Object.entries(cart).reduce((sum, [id, qty]) => sum + findProduct(id).price * qty, 0);
}

function add(id) {
    cart[id] = (cart[id] || 0) + 1;
    tg.HapticFeedback.impactOccurred('light');
    update();
}

function remove(id) {
    cart[id]--;
    if (cart[id] === 0) delete cart[id];
    update();
}

function update() {
    render();
    if (Object.keys(cart).length === 0) closeCart();
    else renderCart();
}

function renderCart() {
    $('cartItems').innerHTML = Object.keys(cart).map((id) => {
        const p = findProduct(id);
        return `<div class="cart-item">
            <img src="/static/images/${p.image}" alt="">
            <div><b>${p.name}</b><br><small>${money(p.price * cart[id])}</small></div>
            ${stepper(id)}
        </div>`;
    }).join('');
    $('submit').textContent = `Оформить заказ · ${money(total())}`;
}

function openCart() {
    renderCart();
    $('cart').hidden = false;
    $('success').hidden = true;
    $('modal').classList.add('open');
    tg.BackButton.show();
}

function closeCart() {
    $('modal').classList.remove('open');
    tg.BackButton.hide();
}

tg.BackButton.onClick(closeCart);
$('modal').onclick = (e) => { if (e.target.id === 'modal') closeCart(); };

// Оформление заказа 

const checkout = $('form').elements;
function validatePhone() {
    const value = checkout.phone.value.replace(/[\s()\-]/g, '');
    checkout.phone.setCustomValidity(value && !/^(?:\+7|8)[0-9]{10}$/.test(value)
        ? 'Введите 11 цифр, начиная с +7 или 8. Например: +7 (999) 123-45-67' : '');
}
checkout.phone.addEventListener('input', validatePhone);
checkout.private_house.addEventListener('change', () => {
    checkout.apartment.required = !checkout.private_house.checked;
    checkout.apartment.disabled = checkout.private_house.checked;
    checkout.apartment.setCustomValidity('');
});
for (const field of ['city', 'street', 'house', 'apartment']) {
    checkout[field].addEventListener('input', () => checkout[field].setCustomValidity(''));
}

$('form').onsubmit = async (e) => {
    e.preventDefault();
    validatePhone();
    for (const field of ['city', 'street', 'house', 'apartment']) {
        const input = checkout[field];
        if (input.disabled) continue;
        input.value = input.value.trim();
        const invalid = !input.value || (['house', 'apartment'].includes(field) && !/[0-9]/.test(input.value));
        input.setCustomValidity(invalid ? 'Укажите ' + ({city:'город', street:'улицу', house:'номер дома', apartment:'номер квартиры'})[field] : '');
    }
    if (!e.target.reportValidity()) return;
    $('submit').disabled = true;

    const order = {
        ...Object.fromEntries(new FormData(e.target)),
        private_house: checkout.private_house.checked,
        items: Object.entries(cart).map(([id, qty]) => ({ id: Number(id), qty })),
        user_id: tg.initDataUnsafe.user?.id,
        user_username: tg.initDataUnsafe.user?.username,
    };

    const response = await fetch('/api/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(order),
    });
    $('submit').disabled = false;

    if (!response.ok) {
        tg.HapticFeedback.notificationOccurred('error');
        alert('Не получилось отправить заказ, попробуйте ещё раз');
        return;
    }

    const { id } = await response.json();
    tg.HapticFeedback.notificationOccurred('success');
    cart = {};
    render();
    $('successTitle').textContent = `Заказ №${id} оформлен`;
    $('cart').hidden = true;
    $('success').hidden = false;
};

load();
