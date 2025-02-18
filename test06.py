import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox, QProgressBar
)
from PyQt5.QtGui import QFont
import pyqtgraph as pg
from datetime import datetime, timedelta
import pymysql
import numpy as np

# Font size settings
ui_font_size = 10
axis_font_size = 14
ticks_font_size = 14
title_font_size = 14



def readDatabaseForAllChannels(start_date, end_date, progress_bar):
    channels = ['plot1', 'plot2', 'plot3', 'plot4']
    return_data = {channel: [[], [], []] for channel in channels}  # {channel: [raw_data, differences, timestamp]}

    db = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='47569', db='labview')
    cursor = db.cursor()

    # Generate the date range
    start_date = datetime.strptime(start_date, '%Y%m%d')
    end_date = datetime.strptime(end_date, '%Y%m%d')

    date_list = [(start_date + timedelta(days=i)).strftime('%Y%m%d') for i in range((end_date - start_date).days + 1)]

    total_data_count = 0
    for date in date_list:
        table_name = f"data{date}"
        try:
            cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            total_data_count += cursor.fetchone()[0]
        except pymysql.err.ProgrammingError as e:
            if e.args[0] == 1146:  # Table does not exist
                print(f"Table '{table_name}' does not exist. Skipping.")
            else:
                print(f"Error reading table '{table_name}': {e}")
                db.rollback()

    progress_bar.setMinimum(0)
    progress_bar.setMaximum(100)

    processed_data_count = 0
    update_threshold = total_data_count * 0.05
    last_update = 0

    for date in date_list:
        table_name = f"data{date}"

        sql_select = f"SELECT ch11, ch12,ch21, ch22, ch31, ch32,ch41, ch42, sensingdate FROM `{table_name}`"
        try:
            cursor.execute(sql_select)
            results = cursor.fetchall()

            for row in results:
                return_data['plot1'][0].append(float(row[0]))
                return_data['plot1'][1].append(float(row[1]))
                # return_data['plot1'][1].append(float(row[0]) - (float(row[1])-m))
                return_data['plot1'][2].append(row[8])

                return_data['plot2'][0].append(float(row[2]))
                return_data['plot2'][1].append(float(row[3]))
                # return_data['plot2'][1].append(float(row[2]) - (float(row[3])-m))
                return_data['plot2'][2].append(row[8])

                return_data['plot3'][0].append(float(row[4]))
                return_data['plot3'][1].append(float(row[5]))
                # return_data['plot3'][1].append(float(row[4]) - (float(row[5])-m))
                return_data['plot3'][2].append(row[8])

                return_data['plot4'][0].append(float(row[6]))
                return_data['plot4'][1].append(float(row[7]))
                # return_data['plot4'][1].append(float(row[6]) - (float(row[7])-m))
                return_data['plot4'][2].append(row[8])

                processed_data_count += 1

                if processed_data_count - last_update >= update_threshold:
                    progress_percentage = (processed_data_count / total_data_count) * 100
                    progress_bar.setValue(int(progress_percentage))
                    last_update = processed_data_count

        except pymysql.err.ProgrammingError as e:
            if e.args[0] == 1146:  # Table does not exist
                print(f"Table '{table_name}' does not exist. Skipping.")
            else:
                print(f"Error reading table '{table_name}': {e}")
                db.rollback()
        except Exception as e:
            print(f"Error reading data: {e}")
            db.rollback()

    progress_bar.setValue(100)
    cursor.close()
    db.close()

    return return_data


def scale_data_to_range(data, reference_data):
    """
    根据reference_data对data进行缩放
    Args:# Prevent division by zero if data is constant
        return [ref_min + (ref_max - ref_min) / 2] * len(data)
        data (list[float]): The data to be scaled.
        reference_data (list[float]): The reference data whose range is used for scaling.
    Returns:
        scaled_data
        scale_factor
        data_min
        ref_min
    """
    ref_min, ref_max = min(reference_data), max(reference_data)
    data_min, data_max = min(data), max(data)

    # print(ref_min) # todo

    if data_min == data_max:
        return [ref_min + (ref_max - ref_min) / 2] * len(data)

    scale_factor = (ref_max - ref_min) / (data_max - data_min)      #  缩放系数
    #scale_factor = (data_max - data_min) / (ref_max - ref_min)
    # Scale the data to match the reference range
    scaled_data = [scale_factor * (x - data_min) + ref_min for x in data]    # x是原始数据，已知什么去反推x

    # print(scale_factor) # todo

    return scaled_data, scale_factor, data_min, ref_min


class SensorPlotApp(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("多通道传感器数据")
        self.setGeometry(100, 100, 1200, 800)

        layout = QVBoxLayout()

        # Date range input fields
        date_layout = QHBoxLayout()
        self.start_date_input = QLineEdit(self)
        self.start_date_input.setPlaceholderText("开始日期 (YYYYMMDD)")
        self.start_date_input.setFont(QFont("Arial", ui_font_size))
        self.end_date_input = QLineEdit(self)
        self.end_date_input.setPlaceholderText("结束日期 (YYYYMMDD)")
        self.end_date_input.setFont(QFont("Arial", ui_font_size))
        start_date_label = QLabel("开始日期：")
        start_date_label.setFont(QFont("Arial", ui_font_size))
        self.start_date_input.setText('20241215')        # 这个时间设置了默认的，可以自己改
        end_date_label = QLabel("结束日期：")
        end_date_label.setFont(QFont("Arial", ui_font_size))
        self.end_date_input.setText('20241215')
        date_layout.addWidget(start_date_label)
        date_layout.addWidget(self.start_date_input)
        date_layout.addWidget(end_date_label)
        date_layout.addWidget(self.end_date_input)

        # Plot button

        # self.plot_button = QPushButton("查询")
        # self.plot_button.setFont(QFont("Arial", ui_font_size))
        # self.plot_button.clicked.connect(self.plot_data)

        # PyQtGraph plot widgets for 5 channels
        self.plots = []
        self.data = {}
        self.linked_view = None

        title_names = ['通道1','通道2','通道3','通道4']

        for i in range(4):
            # plot = pg.PlotWidget(title=f"通道 {i + 1} 数据")
            # plot.setTitle(f"通道 {i + 1} 数据", size=f'{title_font_size}pt')
            plot = pg.PlotWidget(title=f"{title_names[i]}")
            plot.setTitle(f"{title_names[i]}", size=f'{title_font_size}pt')
            plot.getAxis('left').setPen('y')
            plot.setLabel('left', '补偿后波长值', **{'font-size': f'{axis_font_size}pt'})
            plot.setLabel('bottom', '数据点', **{'font-size': f'{axis_font_size}pt'})
            plot.getAxis('left').setStyle(tickFont=QFont("Arial", ticks_font_size))
            plot.getAxis('bottom').setStyle(tickFont=QFont("Arial", ticks_font_size))

            # Synchronize viewboxes across all plots
            if self.linked_view is None:
                self.linked_view = plot.getViewBox()
            else:
                plot.setXLink(self.plots[0])

            plot.scene().sigMouseClicked.connect(lambda event, idx=i: self.on_plot_click(event, idx))
            self.plots.append(plot)

        # Progress bar
        progress_layout = QHBoxLayout()
        self.plot_button = QPushButton("查询")
        self.plot_button.setFont(QFont("Arial", ui_font_size))
        self.plot_button.clicked.connect(self.plot_data)


        self.progress_bar_label = QLabel("查询进度：")
        self.progress_bar_label.setFont(QFont("Arial", ui_font_size))
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.plot_button)
        progress_layout.addWidget(self.progress_bar_label)
        progress_layout.addWidget(self.progress_bar)

        # Add widgets to layout
        layout.addLayout(date_layout)
        # layout.addWidget(self.plot_button)
        layout.addLayout(progress_layout)
        for plot in self.plots:
            layout.addWidget(plot)

        self.setLayout(layout)

    def plot_data(self):
        start_date = self.start_date_input.text()
        end_date = self.end_date_input.text()

        # Validate date input
        try:
            start_dt = datetime.strptime(start_date, "%Y%m%d")
            end_dt = datetime.strptime(end_date, "%Y%m%d")
        except ValueError:
            QMessageBox.critical(self, "日期无效", "请输入有效的日期格式 (YYYYMMDD)。")
            return

        try:
            self.data = readDatabaseForAllChannels(start_date, end_date, self.progress_bar)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据查询失败：{e}")
            return

        for i, (channel, plot) in enumerate(zip(self.data.keys(), self.plots)):
            plot.clear()
            if len(self.data[channel][0]) > 0:
                # Plot raw data
                plot.plot(self.data[channel][0], pen='yellow', name=f"通道 {i + 1} 数据")# 绘制两条图线p1-4
                # Plot differences if available
                if len(self.data[channel][1]) > 0:  # 两条线才用到
                    # scaled_diff, scaled_factor, _, _ = scale_data_to_range(self.data[channel][1], self.data[channel][0])
                    scaled_diff, scaled_factor, data_min, ref_min = scale_data_to_range(self.data[channel][1], self.data[channel][0])
                    plot.plot(scaled_diff, pen='red', name=f"通道 {i + 1} 温补")
                    # print(scaled_diff)

                    # Add a secondary Y-axis
                    axis2 = pg.AxisItem('right')
                    axis2.setPen('r')
                    axis2.setLabel('温补', **{'font-size': f'{axis_font_size}pt'})
                    axis2.setStyle(tickFont=QFont("Arial", ticks_font_size))

                    # Define custom tickStrings method to scale tick values
                    def scaled_tick_strings(values, scale_factor=scaled_factor):
                        return [f"{((v - ref_min) / scale_factor + data_min):.3f}" for v in values]

                    # print(scaled_factor)
                    # print (data_min)

                    # Override the tickStrings method
                    axis2.tickStrings = lambda values, scale, spacing: scaled_tick_strings(values)


                    # def tickStrings ( values, scaled_factor, spacing):
                    #     return [f"{((v - ref_min) / scaled_factor + data_min):.2f}" for v in values]

                    plot.getPlotItem().layout.addItem(axis2, 2, 2)  # Add to the layout
                    axis2.linkToView(plot.getViewBox())
            else:
                QMessageBox.information(self, "无数据", f"通道 {i + 1} 在所选范围内没有数据。")

    def on_plot_click(self, event, plot_index):

        pos = event.scenePos()
        plot = self.plots[plot_index]
        vb = plot.plotItem.vb

        if vb.sceneBoundingRect().contains(pos):
            point = vb.mapSceneToView(pos)
            x, y = point.x(), point.y()

            # Get channel data
            channel = list(self.data.keys())[plot_index]
            raw_data = np.array(self.data[channel][0])

            timestamps = self.data[channel][2]

            if len(raw_data) == 0:  # No data in raw_data
                return

            # Calculate distances to all points in raw_data
            raw_dist = np.abs(np.arange(len(raw_data)) - x) + np.abs(raw_data - y)

            if len(self.data[channel][1]) > 0:  # If diff_data is not empty, calculate distances
                scaled_diff, scaled_factor, data_min, ref_min = scale_data_to_range(self.data[channel][1], self.data[channel][0])
                diff_data = np.array(scaled_diff)
                diff_dist = np.abs(np.arange(len(diff_data)) - x) + np.abs(diff_data - y) # np.abs计算绝对值


                # Find the closest point on either curve
                min_raw_idx = np.argmin(raw_dist)
                min_diff_idx = np.argmin(diff_dist)
                if raw_dist[min_raw_idx] <= diff_dist[min_diff_idx]:
                    closest_idx = min_raw_idx
                    value = raw_data[closest_idx]
                    click_value = value # 浮点型改为 保留小数
                    # label = " "
                else:
                    closest_idx = min_diff_idx
                    value = diff_data[closest_idx]
                    true_diff_value = (value - ref_min) / scaled_factor + data_min
                    click_value = true_diff_value
                    # label = " "

            else:  # Only use raw_data
                closest_idx = np.argmin(raw_dist)
                value = raw_data[closest_idx]
                click_value = value
                label = "原始数据"

            timestamp = timestamps[closest_idx]
            # Clear previous markers
            for item in plot.allChildItems():
                if isinstance(item, pg.TextItem) or isinstance(item, pg.ScatterPlotItem):
                    plot.removeItem(item)

            # Add a text item to display value and timestamp
            if self.data[channel][0]:
                text_item = pg.TextItem(f' {click_value:.3f},  {timestamp}', anchor=(0.5, 1.5))
            else:
                text_item = pg.TextItem(f' {click_value:.1f},  {timestamp}', anchor=(0.5, 1.5))
            text_item.setFont(QFont("Arial", ticks_font_size))
            text_item.setPos(closest_idx, value)
            plot.addItem(text_item)

            # Add a red circular marker at the clicked point
            marker = pg.ScatterPlotItem(size=10, brush='red')
            marker.addPoints([{'pos': (closest_idx, value)}])
            plot.addItem(marker)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = SensorPlotApp()
    window.show()
    sys.exit(app.exec_())
