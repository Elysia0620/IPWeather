import os
import sys
import threading
import requests
from kivy.app import App
from kivy.clock import mainthread
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


# 解决资源读取路径问题（兼容电脑与 Android 打包环境）
def resource_path(relative_path):
    """获取资源的绝对路径"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


# 1. 动态加载项目根目录下的 msyh.ttc 字体（防闪退）
LabelBase.register(name="Roboto", fn_regular=resource_path("msyh.ttc"))


class WeatherApp(App):

    def build(self):
        self.title = "IP / 城市逐小时天气追踪器"

        # 底层根布局（浮动布局，用于背景图叠加）
        root = FloatLayout()

        # 背景图加载 bg.jpg
        bg_path = resource_path("bg.jpg")
        if os.path.exists(bg_path):
            bg = Image(
                source=bg_path,
                allow_stretch=True,
                keep_ratio=False,
                size_hint=(1, 1),
                pos_hint={"x": 0, "y": 0},
                opacity=0.35,  # 透明度 35%
            )
            root.add_widget(bg)

        # 前景主布局
        main_layout = BoxLayout(
            orientation="vertical",
            padding=15,
            spacing=10,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )

        # 顶部位置信息状态显示
        self.location_label = Label(
            text="正在初始化天气数据...",
            size_hint_y=0.05,
            font_size="14sp",
            color=(0.9, 0.9, 1, 1),
            bold=True,
        )
        main_layout.add_widget(self.location_label)

        # 🔍 城市输入框 + 查询按钮 组合区域
        search_box = BoxLayout(
            orientation="horizontal",
            size_hint_y=0.08,
            spacing=8,
        )
        # 修改点：设置默认文本 text="嘉兴"
        self.city_input = TextInput(
            text="嘉兴",
            hint_text="输入城市/县名 (留空则使用 IP 定位)",
            font_name="Roboto",
            font_size="13sp",
            multiline=False,
            size_hint_x=0.7,
            padding=[10, 10, 10, 10],
            background_color=(1, 1, 1, 0.85),
        )
        # 支持按键盘回车直接触发查询
        self.city_input.bind(on_text_validate=self.start_fetch)

        btn = Button(
            text="🔍 查询 / 定位",
            font_name="Roboto",
            size_hint_x=0.3,
            background_color=(0.15, 0.45, 0.85, 0.9),
            font_size="14sp",
        )
        btn.bind(on_press=self.start_fetch)

        search_box.add_widget(self.city_input)
        search_box.add_widget(btn)
        main_layout.add_widget(search_box)

        # 实时天气展示卡片
        self.current_card = BoxLayout(
            orientation="vertical",
            size_hint_y=0.22,
            padding=10,
            spacing=5,
        )
        with self.current_card.canvas.before:
            Color(0, 0, 0, 0.4)
            self.card_bg = Rectangle(
                pos=self.current_card.pos, size=self.current_card.size
            )
        self.current_card.bind(
            pos=self._update_card_bg, size=self._update_card_bg
        )

        self.curr_temp_label = Label(
            text="-- °C",
            font_size="32sp",
            bold=True,
            color=(0.2, 0.8, 1, 1),
        )
        self.curr_details_label = Label(
            text="当前天气 | 湿度: --% | 风速: -- km/h",
            font_size="14sp",
            color=(0.85, 0.85, 0.85, 1),
        )
        self.current_card.add_widget(self.curr_temp_label)
        self.current_card.add_widget(self.curr_details_label)
        main_layout.add_widget(self.current_card)

        # 列表标题
        list_title = Label(
            text="未来逐小时天气预报（温度 / 湿度 / 风速）：",
            size_hint_y=0.05,
            font_size="13sp",
            halign="left",
            color=(0.8, 0.8, 0.8, 1),
        )
        list_title.bind(size=list_title.setter("text_size"))
        main_layout.add_widget(list_title)

        # 可滚动的逐小时天气列表
        self.scroll = ScrollView(size_hint=(1, 0.55))
        self.grid = GridLayout(cols=1, spacing=6, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter("height"))
        self.scroll.add_widget(self.grid)
        main_layout.add_widget(self.scroll)

        root.add_widget(main_layout)
        return root

    def on_start(self):
        # 💡 App 启动时，自动查询默认城市（嘉兴）的天气
        self.start_fetch(None)

    def _update_card_bg(self, instance, value):
        self.card_bg.pos = instance.pos
        self.card_bg.size = instance.size

    def start_fetch(self, instance=None):
        input_text = self.city_input.text.strip()
        if input_text:
            self.location_label.text = f"正在查询 [{input_text}] 的位置与天气..."
        else:
            self.location_label.text = "正在通过 IP 定位并请求天气数据..."

        self.grid.clear_widgets()
        threading.Thread(
            target=self.fetch_weather_data, args=(input_text,), daemon=True
        ).start()

    def fetch_weather_data(self, query_city):
        try:
            lat, lon, location_str = None, None, ""

            # 模式 A：用户输入了城市/县名称
            if query_city:
                geo_url = "https://geocoding-api.open-meteo.com/v1/search"
                geo_params = {
                    "name": query_city,
                    "count": 1,
                    "language": "zh",
                    "format": "json",
                }
                geo_res = requests.get(
                    geo_url, params=geo_params, timeout=10
                ).json()
                results = geo_res.get("results")

                if not results:
                    self.update_status(
                        f"❌ 未找到 [{query_city}]，请检查名字是否正确！"
                    )
                    return

                res = results[0]
                lat = res["latitude"]
                lon = res["longitude"]
                city_name = res.get("name", query_city)
                country = res.get("country", "")
                admin1 = res.get("admin1", "")
                location_str = (
                    f"📍 {country} {admin1} {city_name} (经纬度: {lat:.2f}, {lon:.2f})"
                )

            # 模式 B：框内留空，自动通过 IP 定位
            else:
                ip_res = requests.get("https://ipwho.is/", timeout=10).json()
                if not ip_res.get("success", False):
                    self.update_status("❌ IP 定位失败，请检查网络！")
                    return

                lat = ip_res["latitude"]
                lon = ip_res["longitude"]
                city = ip_res.get("city", "未知城市")
                region = ip_res.get("region", "")
                location_str = f"📍 IP 定位: {region} {city} (经纬度: {lat:.2f}, {lon:.2f})"

            # 统一查询 Open-Meteo 天气数据
            weather_url = (
                f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                "&current=temperature_2m,relative_humidity_2m,wind_speed_10m"
                "&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m&timezone=auto"
            )
            w_res = requests.get(weather_url, timeout=10).json()

            current = w_res.get("current", {})
            curr_temp = current.get("temperature_2m", "--")
            curr_hum = current.get("relative_humidity_2m", "--")
            curr_wind = current.get("wind_speed_10m", "--")

            hourly = w_res.get("hourly", {})
            times = hourly.get("time", [])
            temps = hourly.get("temperature_2m", [])
            hums = hourly.get("relative_humidity_2m", [])
            winds = hourly.get("wind_speed_10m", [])

            self.update_ui(
                location_str,
                curr_temp,
                curr_hum,
                curr_wind,
                times,
                temps,
                hums,
                winds,
            )

        except Exception as e:
            self.update_status(f"❌ 请求失败: {str(e)}")

    @mainthread
    def update_status(self, text):
        self.location_label.text = text

    @mainthread
    def update_ui(
        self,
        location_info,
        curr_temp,
        curr_hum,
        curr_wind,
        times,
        temps,
        hums,
        winds,
    ):
        self.location_label.text = location_info
        self.curr_temp_label.text = f"{curr_temp} °C"
        self.curr_details_label.text = (
            f"当前状态  |  💧 湿度: {curr_hum}%  |  💨 风速: {curr_wind} km/h"
        )

        for t, temp, hum, wind in zip(
            times[:24], temps[:24], hums[:24], winds[:24]
        ):
            time_formatted = t.replace("T", " ")
            row_text = f"⏰ {time_formatted}   |   🌡️ {temp}°C   |   💧 {hum}%   |   💨 {wind} km/h"

            item = Label(
                text=row_text,
                size_hint_y=None,
                height=36,
                font_size="13sp",
                color=(0.95, 0.95, 0.95, 1),
            )
            self.grid.add_widget(item)


if __name__ == "__main__":
    WeatherApp().run()