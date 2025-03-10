import argparse
from itertools import chain
import pprint
import os

from bokeh.embed import components
from bokeh.io import show, output_file, output_notebook
from bokeh.models import ColumnDataSource, FactorRange
from bokeh.plotting import figure
from bokeh.transform import factor_cmap

from . import toolkits
from . import operators
from .utils.common import backend_switcher
from .utils.benchmarks import run_op_frameworks_benchmark

__all__ = ['test_numpy_coverage', 'test_all_operators', 'draw_one_plot', 'test_operators', 'draw_one_backward_plot',
           'generate_operator_reports', 'generate_one_report', 'generate_one_html', 'generate_one_rst']


def test_numpy_coverage(backend_name):
    backend = backend_switcher[backend_name]
    res = {'passed': [], 'failed': []}
    op_list = [i for i in dir(operators) if i[0].isupper()]
    print('Start {0} coverage test!'.format(backend))
    print('#' * 60)
    for op_name in op_list:
        op = getattr(operators, op_name)(backend_name)
        flag = True
        if backend == "jax.numpy":
            func = op.get_forward_func()
            if func:
                try:
                    func(*([{}] * 15))
                except NotImplementedError:
                    res['passed'].append((op_name.lower(), op.__module__.split('.')[-1]))
                except (TypeError, ValueError, AttributeError, RuntimeError):
                    flag = False
                    res['failed'].append((op_name.lower(), op.__module__.split('.')[-1]))
            else:
                flag = False
                res['failed'].append((op_name.lower(), op.__module__.split('.')[-1]))
        else:
            func = op.get_forward_func()
            if func:
                res['passed'].append((op_name.lower(), op.__module__.split('.')[-1]))
            else:
                flag = False
                res['failed'].append((op_name.lower(), op.__module__.split('.')[-1]))
        print("'{0}' under {1} check {2}.".format(op_name.lower(),
                                                  op.__module__.split('.')[-1],
                                                  'passed' if flag else 'failed'))
    print('#' * 60)
    print('End {0} coverage test!'.format(backend))
    return res


def test_all_operators(dtypes='RealTypes', mode='forward', is_random=True, times=6, warmup=10, runs=25):
    backends = ['chainerx', 'jax.numpy', 'mxnet.numpy', 'numpy']
    toolkit_list = dir(toolkits)
    toolkit_list = [i for i in toolkit_list if i.endswith('_toolkit')]
    toolkit_list = [getattr(toolkits, i) for i in toolkit_list]
    result = {}
    for toolkit in toolkit_list:
        name = toolkit.get_name()
        result[name] = run_op_frameworks_benchmark(*toolkit.get_tools(dtypes, is_random),
                                                   backends, mode, times, warmup, runs)
        print("Done benchmark for `{0}`!".format(name))
    return result


def test_operators(toolkit_list, dtypes='RealTypes', mode='forward', is_random=True, times=6, warmup=10, runs=25):
    backends = ['chainerx', 'jax.numpy', 'mxnet.numpy', 'numpy']
    result = {}
    for toolkit in toolkit_list:
        name = toolkit.get_name()
        result[name] = run_op_frameworks_benchmark(*toolkit.get_tools(dtypes, is_random),
                                                   backends, mode, times, warmup, runs)
        print("Done benchmark for `{0}`!".format(name))
    return result


def draw_one_plot(name, data, mode="file", filename="demo.html", info=None):
    title = "NumPy operator {0}".format(name)
    if info:
        title += " - {0}".format(info)
    num = len(data)
    x_labels = ['config{0}'.format(i + 1) for i in range(num)]
    backends = ['numpy', 'mxnet', 'jax', 'chainerx']
    x = [(l, b) for l in x_labels for b in backends]

    if mode == "file":
        output_file(filename)
    else:
        output_notebook()
    palette = ["#756bb1", "#43a2ca", "#e84d60", "#2ca25f"]
    tooltips = [("config", "@configs"), ("latency", "@millisecond ms"), ("std_dev", "@stds ms"), ("speedup", "@rates")]

    configs = list(chain.from_iterable([pprint.pformat(d['config'], width=1)] * 4 for d in data))
    statistics = list(chain.from_iterable((d['numpy'], d['mxnet.numpy'], d['jax.numpy'], d['chainerx']) for d in data))
    millisecond = [i[0] * 1000 if i[0] else None for i in statistics]
    stds = [i[1] * 1000 if i[1] else None for i in statistics]
    rates = list(chain.from_iterable((1.,
                                      d['numpy'][0] / d['mxnet.numpy'][0] if d['mxnet.numpy'][0] else -1,
                                      d['numpy'][0] / d['jax.numpy'][0] if d['jax.numpy'][0] else -1,
                                      d['numpy'][0] / d['chainerx'][0] if d['chainerx'][0] else -1) for d in data))
    offset = -max(rates) / 15
    rates = [r if r > 0 else offset for r in rates]
    source = ColumnDataSource(data=dict(x=x, configs=configs, millisecond=millisecond, rates=rates, stds=stds))
    p = figure(x_range=FactorRange(*x),
               plot_height=600, plot_width=800,
               title=title, y_axis_label="Speedup",
               tooltips=tooltips,
               toolbar_location="above")
    p.vbar(x='x', top='rates', source=source, width=0.9, bottom=offset, line_color="white",
           fill_color=factor_cmap('x', palette=palette, factors=backends, start=1, end=2))
    p.y_range.start = offset
    p.x_range.range_padding = 0.1
    p.xaxis.major_label_orientation = 1
    p.xgrid.grid_line_color = None
    if mode == "file":
        with open(filename, mode='w') as f:
            script, div = components(p)
            f.write(script)
            f.write(div)
    else:
        show(p)


def draw_one_backward_plot(name, data, mode="file", filename="demo.html", info=None):
    title = "NumPy operator {0}".format(name)
    if info:
        title += " - {0}".format(info)
    num = len(data)
    x_labels = ['config{0}'.format(i + 1) for i in range(num)]
    backends = ['mxnet', 'jax', 'chainerx']
    x = [(l, b) for l in x_labels for b in backends]

    if mode == "file":
        output_file(filename)
    else:
        output_notebook()
    palette = ["#43a2ca", "#e84d60", "#2ca25f"]
    tooltips = [("config", "@configs"), ("latency", "@millisecond ms"), ("std_dev", "@stds ms"), ("speedup", "@rates")]

    configs = list(chain.from_iterable([pprint.pformat(d['config'], width=1)] * 3 for d in data))
    statistics = list(chain.from_iterable((d['mxnet.numpy'], d['jax.numpy'], d['chainerx']) for d in data))
    millisecond = [i[0] * 1000 if i[0] else None for i in statistics]
    stds = [i[1] * 1000 if i[1] else None for i in statistics]
    rates = list(chain.from_iterable((1.,
                                      d['mxnet.numpy'][0] / d['jax.numpy'][0] if d['jax.numpy'][0] else -1,
                                      d['mxnet.numpy'][0] / d['chainerx'][0] if d['chainerx'][0] else -1) for d in data))
    offset = -max(rates) / 15
    rates = [r if r > 0 else offset for r in rates]
    source = ColumnDataSource(data=dict(x=x, configs=configs, millisecond=millisecond, rates=rates, stds=stds))
    p = figure(x_range=FactorRange(*x),
               plot_height=530, plot_width=700,
               title=title, y_axis_label="Speedup",
               tooltips=tooltips,
               toolbar_location="right")
    p.vbar(x='x', top='rates', source=source, width=0.9, bottom=offset, line_color="white",
           fill_color=factor_cmap('x', palette=palette, factors=backends, start=1, end=2))
    p.y_range.start = offset
    p.x_range.range_padding = 0.1
    p.xaxis.major_label_orientation = 1
    p.xgrid.grid_line_color = None
    if mode == "file":
        with open(filename, mode='w') as f:
            script, div = components(p)
            f.write(script)
            f.write(div)
    else:
        show(p)


def use_html_template(filename):
    with open(filename, mode="r") as f:
        html = f.readlines()
    html[-1] += '\n'
    html = ["    " + h for h in html]
    html.insert(0, ".. raw:: html\n")
    with open(filename, mode="w") as f:
        f.writelines(html)


def generate_one_rst(toolkit_name, full_update=False):
    toolkit = getattr(toolkits, toolkit_name)
    base_path = os.path.dirname(os.path.abspath(__file__))
    op_name = toolkit.get_name()
    rst_file = os.path.join(base_path, '../doc/reports', op_name + '.rst')
    if os.path.exists(rst_file) and not full_update:
        return True
    content = """Operator `{0}`
==========={1}

""".format(op_name, '=' * len(op_name))
    for dtype in toolkit.get_forward_dtypes():
        html_filename = "{0}_f_{1}.html".format(op_name, dtype)
        content += ".. include:: /_static/temp/{0}\n\n".format(html_filename)
    if toolkit.get_backward_dtypes():
        for dtype in toolkit.get_backward_dtypes():
            html_filename = "{0}_b_{1}.html".format(op_name, dtype)
            content += ".. include:: /_static/temp/{0}\n\n".format(html_filename)
    with open(rst_file, mode='w') as f:
        f.write(content)
    return False


def generate_one_html(toolkit_name, dtype, mode, warmup, runs, info):
    toolkit = getattr(toolkits, toolkit_name)
    base_path = os.path.dirname(os.path.abspath(__file__))
    backends = ['chainerx', 'jax.numpy', 'mxnet.numpy', 'numpy']
    op_name = toolkit.get_name()
    if mode == 'forward':
        html_filename = "{0}_f_{1}.html".format(op_name, dtype)
        html_file = os.path.join(base_path, '../doc/_static/temp', html_filename)
        data = run_op_frameworks_benchmark(*toolkit.get_tools([dtype], False),
                                           backends, 'forward', 6, warmup, runs)
        draw_one_plot(op_name, data, mode='file', filename=html_file,
                      info=info + ", {0}, forward only".format(dtype) if info else None)
        use_html_template(html_file)
    else:
        html_filename = "{0}_b_{1}.html".format(op_name, dtype)
        html_file = os.path.join(base_path, '../doc/_static/temp', html_filename)
        data = run_op_frameworks_benchmark(*toolkit.get_tools([dtype], False),
                                           backends, 'backward', 6, warmup, runs)
        draw_one_backward_plot(op_name, data, mode='file', filename=html_file,
                               info=info + ", {0}, backward only".format(dtype) if info else None)
        use_html_template(html_file)


def generate_one_report(toolkit_name, warmup, runs, info, device="cpu", full_update=False):
    flag = generate_one_rst(toolkit_name, full_update)
    if flag:
        return
    toolkit = getattr(toolkits, toolkit_name)
    op_name = toolkit.get_name()
    for dtype in toolkit.get_forward_dtypes():
        cmd_line = 'python3 -c "from NumpyXBench.tools import generate_one_html; ' \
                   'from NumpyXBench.utils import global_set_{5}; global_set_{5}(); ' \
                   'generate_one_html(\'{0}\', \'{1}\', \'forward\', {2}, {3}, \'{4}\')"'.format(toolkit_name, dtype,
                                                                                                 warmup, runs, info,
                                                                                                 device)
        os.system(cmd_line)
    if toolkit.get_backward_dtypes():
        for dtype in toolkit.get_backward_dtypes():
            cmd_line = 'python3 -c "from NumpyXBench.tools import generate_one_html; ' \
                       'from NumpyXBench.utils import global_set_{5}; global_set_{5}(); ' \
                       'generate_one_html(\'{0}\', \'{1}\', \'backward\', {2}, {3}, \'{4}\')"'.format(toolkit_name,
                                                                                                      dtype, warmup,
                                                                                                      runs, info,
                                                                                                      device)
            os.system(cmd_line)
    print("Done report generation for `{0}`!".format(op_name))


def generate_operator_reports(warmup=10, runs=25, info=None, device="cpu", full_update=False):
    toolkit_list = dir(toolkits)
    toolkit_list = [i for i in toolkit_list if i.endswith('_toolkit')]
    for toolkit_name in toolkit_list:
        # cmd_line = 'python3 -c "from NumpyXBench.tools import generate_one_report; ' \
        #       'generate_one_report(\'{0}\', {1}, {2}, \'{3}\')"'.format(toolkit_name, warmup, runs, info)
        generate_one_report(toolkit_name, warmup, runs, info, device, full_update)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Need parameters 'warmup' and 'runs'.")
    parser.add_argument("--warmup", default=10, type=int)
    parser.add_argument("--runs", default=25, type=int)
    parser.add_argument("--info", default=None, type=str)
    parser.add_argument("--device", default="cpu", type=str)
    parser.add_argument("--full_update", nargs='?', default=False, const=True, type=bool)
    args = parser.parse_args()
    generate_operator_reports(args.warmup, args.runs, args.info, args.device, args.full_update)
