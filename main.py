import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator
import uvicorn

import db
from admin_bot import bot, ADMIN_ID, order_text, order_buttons

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")


class Item(BaseModel):
    id: int
    qty: int


class Order(BaseModel):
    items: list[Item]
    name: str
    phone: str = Field(max_length=40)
    city: str = Field(min_length=1, max_length=100)
    street: str = Field(min_length=1, max_length=160)
    house: str = Field(min_length=1, max_length=30)
    apartment: str = Field(default="", max_length=20)
    private_house: bool = False
    entrance: str = Field(default="", max_length=20)
    floor: str = Field(default="", max_length=20)
    comment: str = ""
    user_id: int | None = None
    user_username: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_]{1,32}$")

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, value):
        compact = re.sub(r"[\s()\-]", "", value)
        if not re.fullmatch(r"(?:\+7|8)[0-9]{10}", compact):
            raise ValueError("Телефон должен начинаться с +7 или 8 и содержать 11 цифр")
        return "+7" + compact[-10:]

    @field_validator("city", "street", "house", "apartment", "entrance", "floor", mode="before")
    @classmethod
    def trim_address(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def valid_address(self):
        if not re.search(r"[0-9]", self.house):
            raise ValueError("Укажите номер дома")
        if not self.private_house and not re.search(r"[0-9]", self.apartment):
            raise ValueError("Укажите номер квартиры или выберите частный дом")
        return self

    @property
    def address(self):
        parts = [self.city, self.street, f"д. {self.house}"]
        if self.private_house:
            parts.append("частный дом")
        else:
            parts.append(f"кв. {self.apartment}")
        if self.entrance:
            parts.append(f"подъезд {self.entrance}")
        if self.floor:
            parts.append(f"этаж {self.floor}")
        return ", ".join(parts)


def load_shop():
    with open("shop.json", encoding="utf-8") as f:
        return json.load(f)


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/api/shop")
async def shop():
    return load_shop()


@app.post("/api/order")
async def create_order(data: Order):
    products = {p["id"]: p for p in load_shop()["products"]}
    items = [
        {"name": products[i.id]["name"], "price": products[i.id]["price"], "qty": i.qty}
        for i in data.items if i.id in products and i.qty > 0
    ]
    if not items or not data.name or not data.phone or not data.address:
        raise HTTPException(400, "Заполните все поля")

    total = sum(i["price"] * i["qty"] for i in items)
    order = db.add_order(items, total, data.name, data.phone, data.address, data.comment, data.user_id, data.user_username)

    await bot.send_message(ADMIN_ID, order_text(order), reply_markup=order_buttons(order))
    return {"id": order["id"]}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
