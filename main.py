import os
import discord
from discord.ext import commands
import requests
import asyncio
import io
import urllib.parse
from collections import Counter
from datetime import datetime, timedelta
import logging

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 设置Discord机器人
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class BotMonitor:
    def __init__(self):
        self.command_usage = Counter()
        self.conversion_success = Counter()
        self.conversion_failure = Counter()
        self.error_types = Counter()
        self.last_reset = datetime.now()

    def log_command(self, command):
        self.command_usage[command] += 1
        logging.info(f"Command used: {command}")

    def log_conversion_success(self, format):
        self.conversion_success[format] += 1
        logging.info(f"Successful conversion to {format}")

    def log_conversion_failure(self, format):
        self.conversion_failure[format] += 1
        logging.error(f"Failed conversion to {format}")

    def log_error(self, error_type):
        self.error_types[error_type] += 1
        logging.error(f"Error occurred: {error_type}")

    def get_stats(self):
        total_conversions = sum(self.conversion_success.values()) + sum(self.conversion_failure.values())
        success_rate = sum(self.conversion_success.values()) / total_conversions if total_conversions > 0 else 0
        stats = f"""
        使用统计（自 {self.last_reset.strftime('%Y-%m-%d %H:%M:%S')}）:
        命令使用次数: {dict(self.command_usage)}
        成功转换次数: {dict(self.conversion_success)}
        失败转换次数: {dict(self.conversion_failure)}
        总体成功率: {success_rate:.2%}
        常见错误类型: {dict(self.error_types)}
        """
        logging.info(f"Stats retrieved: {stats}")
        return stats

    def reset_stats(self):
        logging.info("Stats reset")
        self.__init__()

monitor = BotMonitor()

@bot.event
async def on_ready():
    logging.info(f'{bot.user} has connected to Discord!')
    print(f'{bot.user} has connected to Discord!')
    print("使用 !fc_help 命令可查看使用说明")

    # 从环境变量获取频道ID
    channel_id = os.environ.get('DISCORD_CHANNEL_ID')
    if channel_id:
        channel_id = int(channel_id)
        channel = bot.get_channel(channel_id)
        if channel:
            guide_text = (
                "欢迎使用文件转换机器人！\n\n"
                "使用步骤：\n"
                "1. 上传您要转换的文件\n"
                "2. 在同一条消息中输入 `!convert [目标格式]`\n"
                "3. 等待机器人完成转换并发送结果\n\n"
                "其他有用的命令：\n"
                "`!formats`: 显示支持的文件格式列表\n"
                "`!guide`: 显示详细的使用说明\n"
                "`!fc_help`: 显示快速帮助指南\n\n"
                "如有任何问题，请联系管理员。"
            )
            await channel.send(guide_text)
            logging.info("Welcome message sent to specified channel")
        else:
            logging.error(f"无法找到频道 ID: {channel_id}")
    else:
        logging.warning("未设置 DISCORD_CHANNEL_ID 环境变量")

@bot.command(name='fc_help')
async def file_convert_help(ctx):
    monitor.log_command('fc_help')
    help_text = (
        "文件转换机器人快速指南：\n\n"
        "基本使用步骤：\n"
        "1. 上传您要转换的文件\n"
        "2. 在同一条消息中输入 `!convert [目标格式]`\n"
        "3. 等待机器人完成转换并发送结果\n\n"
        "其他有用的命令：\n"
        "`!formats`: 显示支持的文件格式列表\n"
        "`!guide`: 显示详细的使用说明\n\n"
        "如需更多帮助，请输入 `!guide` 查看完整指南。\n"
        "祝您使用愉快！"
    )
    await ctx.send(help_text)
    logging.info("Help command executed")

@bot.command(name='guide')
async def show_guide(ctx):
    monitor.log_command('guide')
    guide_text = (
        "文件转换机器人使用指南：\n\n"
        "1. `!convert [格式]`：转换上传的文件到指定格式。\n"
        " 例如：上传文件后输入 `!convert pdf`\n\n"
        "2. `!formats`：显示支持的文件格式列表。\n\n"
        "3. `!guide`：显示此帮助信息。\n\n"
        "4. `!fc_help`：显示快速帮助指南。\n\n"
        "使用步骤：\n"
        "1. 上传您要转换的文件\n"
        "2. 在同一条消息中输入 `!convert [目标格式]`\n"
        "3. 等待机器人完成转换并发送结果\n\n"
        "如有任何问题，请联系管理员。"
    )
    await ctx.send(guide_text)
    logging.info("Guide command executed")

@bot.command(name='formats')
async def show_formats(ctx):
    monitor.log_command('formats')
    await ctx.send("支持的格式有：PDF, DOCX, JPG, PNG, PPTX, BMP, TIFF, SVG, EPUB, MOBI 等。\n"
                   "使用方法：请上传文件并输入 !convert [目标格式]，例如 !convert pdf")
    logging.info("Formats command executed")

@bot.command(name='convert')
async def convert_file(ctx, output_format: str):
    monitor.log_command('convert')
    if not ctx.message.attachments:
        await ctx.send("请附加一个文件到您的消息中。")
        logging.warning("Convert command used without file attachment")
        return

    attachment = ctx.message.attachments[0]
    file_url = attachment.url
    original_filename = attachment.filename

    # 解码文件名（处理中文字符）
    original_filename = urllib.parse.unquote(original_filename)

    # 获取文件名（不包括扩展名）
    file_name_without_ext = os.path.splitext(original_filename)[0]

    await ctx.send(f"开始将文件 {original_filename} 转换为 {output_format} 格式...")
    logging.info(f"Starting conversion of {original_filename} to {output_format}")

    try:
        response = requests.post('https://api.convertio.co/convert', json={
            'apikey': os.environ['CONVERTIO_API_KEY'],
            'input': 'url',
            'file': file_url,
            'outputformat': output_format,
            'filename': original_filename
        })

        if response.status_code == 200:
            data = response.json()
            conversion_id = data['data']['id']

            while True:
                status_response = requests.get(f'https://api.convertio.co/convert/{conversion_id}/status')
                status_data = status_response.json()

                if status_data['data']['step'] == 'finish':
                    result_url = status_data['data']['output']['url']
                    # 下载转换后的文件
                    file_response = requests.get(result_url)
                    if file_response.status_code == 200:
                        file_content = io.BytesIO(file_response.content)
                        new_filename = f"{file_name_without_ext}.{output_format}"
                        # 将文件作为附件发送，使用新的文件名
                        await ctx.send(f"文件 {original_filename} 已成功转换为 {output_format} 格式！",
                                       file=discord.File(file_content, filename=new_filename))
                        monitor.log_conversion_success(output_format)
                        logging.info(f"File {original_filename} successfully converted to {output_format}")
                    else:
                        await ctx.send("无法下载转换后的文件。请稍后再试。")
                        monitor.log_conversion_failure(output_format)
                        logging.error(f"Failed to download converted file. Status code: {file_response.status_code}")
                    break
                elif status_data['data']['step'] == 'error':
                    await ctx.send("转换过程中出现错误。")
                    monitor.log_conversion_failure(output_format)
                    logging.error(f"Error during conversion process: {status_data.get('data', {}).get('error', 'Unknown error')}")
                    break

                await asyncio.sleep(5)
        else:
            await ctx.send("启动转换过程时出错。请稍后再试。")
            monitor.log_conversion_failure(output_format)
            logging.error(f"Error initiating conversion process. Status code: {response.status_code}")
    except Exception as e:
        await ctx.send(f"发生错误：{str(e)}")
        monitor.log_error(type(e).__name__)
        logging.exception("Exception occurred during file conversion")

@convert_file.error
async def convert_file_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("请指定输出格式。使用方法：!convert [目标格式]，例如 !convert pdf\n"
                       "要查看支持的格式列表，请使用 !formats 命令。")
    else:
        await ctx.send(f"发生错误：{str(error)}")
    monitor.log_error(type(error).__name__)
    logging.error(f"Error in convert_file command: {error}")

@bot.command(name='stats')
@commands.has_permissions(administrator=True)
async def show_stats(ctx):
    monitor.log_command('stats')
    await ctx.send(monitor.get_stats())
    logging.info("Stats command executed")

@bot.command(name='reset_stats')
@commands.has_permissions(administrator=True)
async def reset_stats(ctx):
    monitor.log_command('reset_stats')
    monitor.reset_stats()
    await ctx.send("统计数据已重置。")
    logging.info("Stats reset")

if __name__ == "__main__":
    logging.info("Starting main.py")
    try:
        bot.run(os.environ['DISCORD_TOKEN'])
    except Exception as e:
        logging.critical(f"Failed to start the bot: {e}")
