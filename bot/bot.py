import discord
from discord import app_commands
from discord.ext import commands
import json
import os

# --- НАСТРОЙКА БОТА ---
intents = discord.Intents.default()
intents.message_content = True

class VPIBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.data_file = "economy.json"

    async def setup_hook(self):
        # Синхронизация слеш-команд
        await self.tree.sync()
        print(f"Система синхронизирована. Бот запущен как {self.user}")

    def load_data(self):
        """Загрузка данных из JSON файла"""
        if os.path.exists(self.data_file):
            with open(self.data_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_data(self, data):
        """Сохранение данных в JSON файл"""
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def get_user_data(self, data, user_id):
        """Получение данных игрока или создание дефолтных"""
        u_id = str(user_id)
        if u_id not in data:
            data[u_id] = {"money": 1000, "country": "Неизвестно"}
        return data[u_id]

bot = VPIBot()

# --- КОМАНДЫ ---

@bot.tree.command(name="stats", description="📊 Показать статистику вашего государства")
async def stats(interaction: discord.Interaction):
    data = bot.load_data()
    user_stats = bot.get_user_data(data, interaction.user.id)
    bot.save_data(data) # Сохраняем на случай создания нового профиля

    embed = discord.Embed(
        title=f"🏛️ Государственная сводка: {interaction.user.display_name}",
        color=discord.Color.gold()
    )
    embed.add_field(name="🏳️ Название державы", value=f"**{user_stats['country']}**", inline=False)
    embed.add_field(name="💰 Золотой запас", value=f"`{user_stats['money']}` 🪙", inline=True)
    embed.set_footer(text="Мировая арена ждет ваших решений")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="set_country", description="👑 Назначить игроку название государства (Только для Администрации)")
@app_commands.checks.has_permissions(administrator=True)
async def set_country(interaction: discord.Interaction, member: discord.Member, name: str):
    data = bot.load_data()
    bot.get_user_data(data, member.id) # Гарантируем наличие профиля
    
    old_name = data[str(member.id)]["country"]
    data[str(member.id)]["country"] = name
    bot.save_data(data)
    
    embed = discord.Embed(
        title="📝 Регистрация новой державы",
        description=f"Администратор {interaction.user.mention} изменил статус игрока!",
        color=discord.Color.blue()
    )
    embed.add_field(name="Правитель", value=member.mention, inline=True)
    embed.add_field(name="Новое имя", value=f"**{name}**", inline=True)
    embed.set_footer(text=f"Старое название: {old_name}")
    
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="pay", description="💸 Перевести золото другому государству")
async def pay(interaction: discord.Interaction, recipient: discord.Member, amount: int):
    if amount <= 0:
        await interaction.response.send_message("Сумма должна быть больше нуля!", ephemeral=True)
        return

    if recipient.id == interaction.user.id:
        await interaction.response.send_message("Вы не можете переводить деньги самому себе!", ephemeral=True)
        return

    data = bot.load_data()
    sender_id = str(interaction.user.id)
    recipient_id = str(recipient.id)

    # Убеждаемся, что оба игрока в базе
    sender_data = bot.get_user_data(data, sender_id)
    recipient_data = bot.get_user_data(data, recipient_id)

    if sender_data["money"] < amount:
        await interaction.response.send_message(
            f"❌ В вашей казне недостаточно средств! Баланс: `{sender_data['money']}` 🪙", 
            ephemeral=True
        )
        return

    # Проведение транзакции
    sender_data["money"] -= amount
    recipient_data["money"] += amount
    
    bot.save_data(data)

    embed = discord.Embed(
        title="🤝 Международная транзакция",
        description=f"Перевод средств между государствами прошел успешно!",
        color=discord.Color.green()
    )
    embed.add_field(name="Отправитель", value=f"{interaction.user.mention}\n({sender_data['country']})", inline=True)
    embed.add_field(name="Получатель", value=f"{recipient.mention}\n({recipient_data['country']})", inline=True)
    embed.add_field(name="Сумма перевода", value=f"`{amount}` 🪙", inline=False)
    
    await interaction.response.send_message(embed=embed)


# --- ОБРАБОТКА ОШИБОК ---

@set_country.error
async def set_country_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "🛑 Ошибка доступа: У вас нет полномочий изменять границы государств!", 
            ephemeral=True
        )
