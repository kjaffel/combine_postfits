from __future__ import annotations
from collections import defaultdict
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from typeguard import typechecked
import logging
import pprint
import numpy as np
from scipy import stats
from matplotlib.offsetbox import AnchoredText
import mplhep as hep
import hist
from copy import deepcopy

from .utils import cmap10
from .utils import extract_mergemap, fill_colors
from .utils import format_legend, format_categories
from .utils import get_fit_val, get_fit_unc
from .utils import getha, geths, geth, merge_hists

np.seterr(divide="ignore", invalid="ignore")

# set up pretty printer for logging
pp = pprint.PrettyPrinter(indent=2, sort_dicts=False)


def log_pretty(obj):
    pretty_out = f"{pp.pformat(obj)}"

    return f"{pretty_out}\n"


@typechecked
def plot(
    fitDiag_uproot,
    fit_type: str = "prefit",  # 'prefit' | 'fit_s' | 'fit_b'
    cats: str | list[str] | None = None,
    # Sample plotting opts
    sigs: (
        list[str] | None
    ) = None,  # List of samples considered signals, by default matches to `total_signal`
    bkgs: (
        list[str] | None
    ) = None,  # List of samples considered backaground - exclude QCD
    onto: str | None = None,  # large background to plot others onto typically QCD
    project: (
        list[str] | None
    ) = None,  # Project (duplicate) some samples onto the x-axis for readability
    project_signal: (
        list[float | int] | None
    ) = None,  # Plot projected total signal on x-axis, scale by `project_signal`
    blind: bool = False,  # Blind data
    remove_tiny: (
        bool | float | int | str
    ) = False,  # Remove enteries with total yield below treshold eg. {False | 10 | '5%'}
    # Style opts
    restoreNorm=True,  # Combine outputs binwnormed results - restores to nominal
    fitDiag_root=None,  # ROOT fitDiagnostics file to read fit results and display signal strength
    rmap: dict | None = None,
    style: dict | None = None,  # Style YAML
    merge: (
        dict[str, list] | None
    ) = None,  # {new_key: [old_key1, old_key2]} overwrites settings in style yaml
    clipx: bool = False,  # Clip edge bins when empty
    cat_info: (
        bool | int | str
    ) = 2,  # Number of category names to display per line. Set ``False`` to disable cat info. Set to str to display custom text.
    chi2: bool = False,  # Calculate and display chi2 of data to total shapes
    chi2_nocorr: bool = False,  # Calculate and display chi2 of data to total shape
    residuals: bool = False,  # Calculated and display chi2 of data to total shapes
) -> tuple:
    # Prep
    style = style.copy()
    fit_shapes_name = f"shapes_{fit_type}"
    if cats is None:
        cats = [fitDiag_uproot[f"{fit_shapes_name}"].keys()[0].split(";")[0]]
    elif isinstance(cats, str):
        cats = [cats]
    logging.info(f"Plotting `{fit_shapes_name}` for categories: {','.join(cats)}.")
    if restoreNorm:
        logging.info(
            f"  restoreNorm={restoreNorm}: bin-width normalization from combine will be restored."
        )
    if merge is None and style is not None:
        merge = extract_mergemap(style)
    logging.debug(f"  Merge mapping: {merge}")
    if sigs is None:
        sigs = []
    if bkgs is None:
        bkgs = []
    if project is None:
        project = []
    # Fetch hists
    channels = [fitDiag_uproot[f"{fit_shapes_name}/{cat}"] for cat in cats]
    if len(channels) == 0:
        return None, (None, None)
    orig_hist_keys = [
        k.split(";")[0]
        for k in list(set(sum([c.keys() for c in channels], [])))
        if "data" not in k and "covar" not in k
    ]
    data = getha("data", channels, restoreNorm=restoreNorm)
    hist_dict = geths(
        orig_hist_keys,
        channels,
        restoreNorm=restoreNorm,
        style_dict=None,
    )
    tot_bkg = getha("total_background", channels, restoreNorm=restoreNorm)
    tot = getha("total", channels, restoreNorm=restoreNorm)
    # Prepare merges
    hist_dict = merge_hists(hist_dict, merge)
    hist_keys = list(hist_dict.keys())
    _merged_away = []
    for k, v in merge.items():
        _merged_away += v
    # Check if all available
    for key in sigs + bkgs + project:
        if key not in hist_dict.keys():
            logging.warning(
                f"  Hist '{key}' is missing and will be ignored. Available keys are: {hist_keys}"
            )

    # Soft-fail on missing hist
    def hist_dict_fcn(name, raw=False, global_scale=True, th=0.003):
        """
        raw: return raw hist without any modifications
        global_scale: when true will clip small values based on global max, else based on hist max
                set to False when plotting eg. signal in ratio
        """
        _max_value_global = np.max([np.max(h.values()) for h in hist_dict.values()])
        if name not in hist_dict:
            logging.warning(f"  Hist '{name}' is missing. Will be replaced with zeros.")
            _hobj = deepcopy(hist_dict[list(hist_dict.keys())[0]])
            _hobj.view().value *= 0
            _hobj.view().variance *= 0
            return _hobj
        _hobj = deepcopy(hist_dict[name])
        if raw:
            return _hobj
        # Convert zeros to nans for plotting (lw>0)
        if np.any(_hobj.values() < 0):  # negative hists
            _th = th * np.min(_hobj.values())
            non_zero_indices = np.where(_hobj.values() < _th)[0]
        else:  # positive hists
            _th = th * (
                np.max(_max_value_global) if global_scale else np.max(_hobj.values())
            )
            non_zero_indices = np.where(_hobj.values() > _th)[0]
        if len(non_zero_indices) != len(_hobj.values()) and non_zero_indices.size > 1:
            logging.debug(
                f"  Hist '{name}' has values < '{_th:.3f}'. Setting to NaNs: {[f'{v:.2f}' for v in _hobj.values()]}."
            )
            _hobj.view().value[: non_zero_indices[0]] = np.nan
            _hobj.view().value[non_zero_indices[-1] + 1 :] = np.nan
            # if len(non_zero_indices) != len(_hobj.values()):
            logging.debug(
                f"  Hist '{name}' had values < '{_th:.3f}'. Now set to NaNs: {[f'{v:.2f}' for v in _hobj.values()]}."
            )
        return _hobj

    # Remove tiny
    if remove_tiny:
        if isinstance(remove_tiny, str) and remove_tiny.endswith("%"):
            _th = float(remove_tiny[:-1]) * 0.005 * np.sum(data.values())
        elif remove_tiny is True:
            _th = 0.05 * np.sum(data.values())
        elif np.isnumeric(remove_tiny):
            _th = remove_tiny
        else:
            raise ValueError(f"Kwarg `remove_tiny={remove_tiny}` not understood.")
        for key in hist_keys:
            if key in bkgs + sigs + project:
                continue
            if np.sum(hist_dict_fcn(key).values()) < _th:
                logging.info(
                    f"  Skipping hist {key}: because its yield is below threshold."
                )
                hist_keys.remove(key)

    # Fetch keys
    if "total_signal" not in list(
        set(sum([c.keys() for c in channels], []))
    ):  # no signal in CRs
        default_signal = []
    else:
        default_signal = [
            k
            for k in orig_hist_keys
            if k in channels[0]
            and channels[0][k] == channels[0]["total_signal"]
            and "total" not in k
        ]
    default_bkgs = [
        k
        for k in hist_keys
        if k not in default_signal
        and k != onto
        and "total" not in k
        and k not in _merged_away
    ]
    _sortable, _extra = (
        [k for k in default_bkgs if k in style.keys()],
        [k for k in default_bkgs if k not in style.keys()],
    )
    default_bkgs = ([k for k in style.keys() if k in _sortable] + _extra)[::-1]
    if len(bkgs) == 0:
        bkgs = default_bkgs
    if len(sigs) > 2:
        raise ValueError(
            "Are you insane? More than 2 signals? Write your own plotter lol."
        )
    elif len(sigs) == 0:
        if len(default_signal) == 1:
            sigs = default_signal
            logging.info(
                f"  Signal {default_signal[0]} picked automatically by matching to `total_signal`."
            )
        else:
            logging.warning(
                f"  No default signal was found. Can be set with the `sigs` kwarg. Choices are: {hist_keys}"
            )
    bkgs = [bkg for bkg in bkgs if bkg != onto and bkg not in sigs]
    # Remove negatives from backgrounds/stackable:
    sigs_original = sigs.copy()  # Allow negatives in ratio
    _sigs, _bkgs, _excluded = [], [], []
    for list_in, list_out in zip([sigs, bkgs], [_sigs, _bkgs]):
        for key in list_in:
            if key not in style:
                raise KeyError(
                    f"Hist '{key}' not in style dict. Available keys include: {list(style.keys())}."
                )
            if key not in hist_keys:
                logging.warning(
                    f"  Hist '{key}' is not available for '{fit_type}' in the input file."
                )
                continue
            if np.any(hist_dict_fcn(key, raw=True).values() < 0):
                _excluded.append(key)
                logging.warning(
                    f"  Hist '{key}' has negative values and will not be show in the stack"
                )
                logging.debug(f"  Hist {key}: {hist_dict_fcn(key).values()}")
            else:
                list_out.append(key)
    sigs = _sigs
    bkgs = _bkgs
    logging.info(f"  Signals: {','.join(sigs)}.")
    logging.info(f"  Backgrounds: {','.join(bkgs)}.")
    logging.info(f"  Onto bkg: {onto}.")
    unused = [
        key
        for key in hist_keys
        if key not in sigs + bkgs + project + [onto]
        and "total" not in key
        and key not in _merged_away
        and key not in _excluded
    ]
    if len(unused) > 0:
        logging.warning(
            f"  Samples: {unused} are available in the workspace, but not included to be plotted."
        )
    for key in sigs + bkgs:
        if key not in style.keys() and key not in _merged_away:
            logging.warning(
                f"  Key `{key} is not available in `styles`. Will autofill",
            )
            style[key] = {"label": key}
    style = fill_colors(style, cmap=cmap10, no_duplicates=False)
    logging.debug(f"  Style: \n{log_pretty(style)}")

    ###############
    # Plotting main
    logging.debug(f"  DEBUG: Main plotting")
    fig, (ax, rax) = plt.subplots(
        2, 1, gridspec_kw={"height_ratios": (3, 1)}, sharex=True
    )
    plt.subplots_adjust(hspace=0)
    if onto is None:
        hep.histplot(
            [hist_dict_fcn(k) for k in bkgs + sigs],
            ax=ax,
            label=bkgs + sigs,
            stack=True,
            histtype="fill",
            facecolor=[style[k]["color"] for k in bkgs + sigs],
        )
    else:
        if onto in hist_dict.keys():
            hep.histplot(
                hist_dict_fcn(onto),
                ax=ax,
                label=onto,
                yerr=False,  # facecolor='none',
                histtype="step",
                color=style[onto]["color"],
                hatch=style[onto]["hatch"],
                lw=2,
                zorder=2,
            )
        _hatch = [None, *[style[k]["hatch"] for k in bkgs + sigs]]
        _edgecolor = [
            style[k]["color"] if h not in ["none", None] else None
            for k, h in zip([onto] + bkgs + sigs, _hatch)
        ]
        _facecolor = [
            "none" if h not in ["none", None] or k == onto else style[k]["color"]
            for k, h in zip([onto] + bkgs + sigs, _hatch)
        ]
        _linewidth = [2] + [
            0 if h not in ["none", None] else 0 for k, h in zip(bkgs + sigs, _hatch[1:])
        ]
        hep.histplot(
            [
                hist_dict_fcn(onto),
                *[hist_dict_fcn(k, global_scale=False, th=0.02) for k in bkgs + sigs],
            ],
            ax=ax,
            label=["_", *(bkgs + sigs)],
            stack=True,
            histtype="fill",
            facecolor=_facecolor,
            edgecolor=_edgecolor,
            hatch=_hatch,
            linewidth=_linewidth,
        )
    if not blind:
        hep.histplot(
            data,
            ax=ax,
            label="data",
            xerr=True,
            histtype="errorbar",
            color="k",
            zorder=4,
        )

    logging.debug(f"  DEBUG: Projections")
    # Ploting projection
    if len(project) != 0:
        logging.info(f"  Projecting on x-axis: {','.join(project)}")
        hep.histplot(
            [hist_dict_fcn(k) for k in project],
            ax=ax,
            facecolor=[style[k]["color"] for k in project],
            stack=True,
            histtype="fill",
        )

    # Project signal
    if rmap is None:
        if len(sigs) == 1:
            rmap = {sigs_original[0]: "r"}
        else:
            logging.warning(
                f"  No `--rmap` passed. Automatic inference wasn't possible. Signal strengths won't be shown."
            )
    if project_signal is not None:
        _rs = dict(zip(sigs_original, [1] * len(sigs_original)))
        if fit_type == "prefit":
            pass
        elif fitDiag_root is None:
            logging.warning(
                "  Kwarg `fitDiag_root` was not passed. Postfit signal strengths are unavailable. "
                "Kwarg `project_signal` will be scaling the postfit distribution: `nominal * r * project_signal`. "
                "When `fitDiag_root` is available, signal strength gets factored out resulting in: `nominal * project_signal`."
            )
        else:
            if rmap is None:
                raise ValueError(
                    "Cannot infer sample:poi mapping for more than 1 signal. Pass e.g. "
                    "rmap={'hbb': 'r', 'hcc':'r2'}"
                )
            else:
                _rs = {
                    sig: get_fit_val(
                        fitDiag_root, rmap[sig], fittype=fit_type, substitute=1.0
                    )
                    for sig in rmap
                }
        sig_dicts = defaultdict(lambda: 0)
        for sig, proj in zip(sigs_original, project_signal):
            sig_dicts[sig] = proj
        logging.info(
            f"  Projecting signal on x-axis: {'; '.join([f'{k}:{v:.2f}' for k, v in _rs.items()])}"
        )
        for j, sig in enumerate(sigs_original):
            if sig_dicts[sig] == 0 or sig not in hist_keys:
                continue
            _scaled_sig = (
                hist_dict_fcn(sig, global_scale=False, th=0.05)
                * sig_dicts[sig]
                / _rs[sig]
            )
            _p_label = (
                style[sig]["label"]
                if sig_dicts[sig] == 1
                else f"{style[sig]['label']} x {sig_dicts[sig]:.0f}"
            )
            hep.histplot(
                _scaled_sig,
                ax=ax,
                color=style[sig]["color"],
                stack=True,
                histtype="step",
                label=_p_label,
                yerr=False,
                ls="dashed",
                lw=2,
            )

    logging.debug(f"  DEBUG: Ratios")
    #########
    # Subplot/ratio
    rh_unc = np.zeros_like(data.values())
    if not blind:
        # rh = (data.values() - tot_bkg.values()) / np.sqrt(data.variances())
        rh = data.values() - tot_bkg.values()
        _lo, _hi = np.abs(
            hep.error_estimation.poisson_interval(data.values(), data.variances())
            - data.values()
        )
        rh_unc[rh < 0] = _hi[rh < 0]
        rh_unc[rh > 0] = _lo[rh > 0]
        rh /= rh_unc
        ## Plotting subplot
        hep.histplot(
            rh,
            data.axes[0].edges,
            ax=rax,
            yerr=1,
            histtype="errorbar",
            color="k",
            xerr=True,
            zorder=4,
        )
    # Signal plotting
    # Plot total signal if sum of matched signals doesn't match total, emit warning
    if not np.round(
        np.sum([hist_dict_fcn(sig, raw=True).values() for sig in sigs_original])
    ) == np.round(np.sum(hist_dict_fcn("total_signal", raw=True).values())):
        logging.warning(
            f"  Sum of specified signals: {sigs_original} does not match 'total_signal'. Will plot 'total_signal' in the ratio instead."
        )
        sigs_original = ["total_signal"]
    if len(sigs_original) > 0 and np.any(
        [sig in hist_keys for sig in sigs_original]
    ):  # No signals in CRs
        # Plotted signals should match total_signal, replace if not
        _hatch = [style[sig]["hatch"] for sig in sigs_original]
        _edgecolor = [
            style[k]["color"] if h not in ["none", None] else "none"
            for k, h in zip(sigs_original, _hatch)
        ]
        _facecolor = [
            "none" if h not in ["none", None] else style[k]["color"]
            for k, h in zip(sigs_original, _hatch)
        ]
        _lw = [0 if h not in ["none", None] else 0 for h in _hatch]
        hep.histplot(
            [
                hist_dict_fcn(sig, global_scale=False, th=0.05) / rh_unc
                for sig in sigs_original
            ],
            ax=rax,
            facecolor=_facecolor,
            edgecolor=_edgecolor,
            hatch=_hatch,
            lw=_lw,
            stack=True,
            histtype="fill",
            label=[style[sig]["label"] for sig in sigs_original],
        )
    ## Bkg Unc
    if np.sum(tot_bkg.variances()) == 0:
        logging.warning(
            "  Background uncertainties not available (are 0) in fitDiagnostics file. "
            "Fit may not have converged correctly."
        )
    logging.debug(
        f"  yerr - bkg variances (raw): {np.sqrt(tot_bkg.variances() * tot_bkg.axes[0].widths) }."
    )
    yerr_nom = np.sqrt(tot_bkg.variances() * tot_bkg.axes[0].widths) / np.sqrt(
        data.variances() * tot_bkg.axes[0].widths
    )
    yerr = yerr_nom.copy()
    logging.debug(f"  yerr (raw): {yerr}.")
    yerr[~np.isfinite(yerr_nom)] = 0
    if "rh" in locals():
        err_th = np.max([7, 1.5 * np.max(abs(np.r_[0.01, rh[np.isfinite(rh)]]))])
    else:
        err_th = 7
    good_yerr_mask = yerr < err_th  # Data unc is 1 by definiton
    hep.histplot(
        np.zeros_like(data.values()),
        tot_bkg.axes[0].edges,
        ax=rax,
        yerr=[yerr, yerr],
        histtype="band",
        label="Bkg. Unc.",
        zorder=-1,
    )

    if np.sum(~good_yerr_mask) > 1:
        logging.warning(
            f"  Bkg. Unc. in {np.sum(~good_yerr_mask)} bins is very large ( > {err_th}) this may be pathological. Full uncertainty is: {yerr_nom}"
        )

    logging.debug(f"  DEBUG: Styling")
    #########
    # Styling
    ax.legend(ncol=2)

    # Axis limits
    if clipx:
        _h, _bins = data.copy().to_numpy()
        _h += tot_bkg.to_numpy()[0]
        if len(_bins) > 2:
            nonzero_left = _bins[:-1][_h > 0]
            nonzero_right = _bins[1:][_h > 0]
            ax.set_xlim(nonzero_left[0], nonzero_right[-1])
            rax.set_xlim(nonzero_left[0], nonzero_right[-1])
        else:  # Single bin
            ax.set_xlim(_bins[0], _bins[-1])
            rax.set_xlim(_bins[0], _bins[-1])
    else:
        ax.set_xlim(data.axes[0].edges[0], data.axes[0].edges[-1])

    # Axis labels
    ax.set_xlabel(None)
    rax.set_xlabel(tot_bkg.axes[0].label)
    if restoreNorm:
        if np.std(data.axes[0].widths) == 0:
            _binwidth = f"{np.mean(data.axes[0].widths):.0f}"
        else:
            _binwidth = f"{stats.mode(np.mean(data.axes[0].widths)).mode:.0f}"
            _binwidth = ""
            logging.warning(
                "  Bin-width is not constant. Consider setting custom y-label"
            )
        ax.set_ylabel(f"Events / {_binwidth}GeV")
    else:
        ax.set_ylabel("Events / GeV")

    # Ratio
    limlo, limhi = rax.get_ylim()
    if "rh" in locals():
        rax.set_ylim(
            np.min([-2, np.nanmin(rh) * 1.5 - 1]), np.max([2, 1 + np.nanmax(rh) * 1.5])
        )
    else:
        rax.set_ylim(np.min([-2, limlo]), np.max([2, limhi * 1.8]))
    rax.axhline(0, color="gray", ls="--")
    rax.set_ylabel(r"$\frac{Data-Bkg}{\sigma_{Data}}$", y=0.5)

    logging.debug(f"  DEBUG: Legend format")
    # Reformatting legend
    existing_keys = ax.get_legend_handles_labels()[-1]
    for key in existing_keys:
        if key not in style.keys():
            style[key] = {"label": key}
    order = np.argsort([list(style.keys()).index(i) for i in existing_keys])
    handles, labels = ax.get_legend_handles_labels()
    handles = [handles[i] for i in order]
    labels = [style[labels[i]]["label"] for i in order]
    _legend_fontsize = "small" if len(labels) <= 8 else "x-small"
    leg = format_legend(
        ax,
        ncols=2,
        handles_labels=(handles, labels),
        bbox_to_anchor=(1, 1),
        markerscale=0.8,
        fontsize=_legend_fontsize,
        labelspacing=0.4,
        columnspacing=1.5,
    )
    hep.yscale_legend(ax, soft_fail=True)
    if fit_type == "prefit":
        leg.set_title(title=fit_type.capitalize(), prop={"size": "small"})
    else:
        # Don't write postfit to save space, just print r
        if fitDiag_root is None:
            leg.set_title(title="Postfit", prop={"size": "small"})
        else:
            # Write signal strengths
            leg.set_title(title=None, prop={"size": "small"})
            fig.canvas.draw()
            mu_strs = []
            for sig in sigs_original:
                if rmap is None or sig not in rmap or sig not in hist_keys:
                    continue
                logging.debug(
                    f"  Reading signal strength for '{sig}' from parameter '{rmap[sig]}'."
                )
                _r = get_fit_val(
                    fitDiag_root,
                    rmap[sig],
                    fittype=fit_type,
                    substitute=None,
                )
                if _r is None:
                    leg.set_title(title="Postfit", prop={"size": "small"})
                    continue
                _r = rf"{_r:.2f}"
                _d, _u = get_fit_unc(
                    fitDiag_root,
                    rmap[sig],
                    fittype=fit_type,
                    substitute=(0, 0),
                )
                _d, _u = rf"{_d:.2f}", f"{_u:.2f}"
                mu_strs.append(
                    r"$\mu_{%s}$ = " % style[sig]["label"].replace("$", "")
                    + r"${%s}_{%s}^{%s}$" % (_r, _d, _u)
                )
            if len(mu_strs) > 0 and not blind:
                fig.canvas.draw()
                bbox = leg.get_window_extent().transformed(ax.transAxes.inverted())
                x, y = bbox.xmin + bbox.width / 2, bbox.ymin
                ax.text(
                    x,
                    y,
                    # "  ".join(mu_strs),
                    "\n".join(mu_strs),
                    fontsize="x-small",
                    ha="center",
                    va="top",
                    transform=ax.transAxes,
                )
                ax.set_ylim(None, ax.get_ylim()[-1] * 1.05)

    # Ratio legend
    ncol = 3 if not residuals else 1
    rax.legend(ncol=ncol)  # dummy legend
    handles, labels = ax.get_legend_handles_labels()
    rax.legend(
        loc="upper right",
        ncol=ncol,
        markerscale=0.8,
        fontsize="xx-small" if len(labels) > 2 else _legend_fontsize,
        labelspacing=0.4,
        columnspacing=1.5,
    )
    hep.yscale_legend(rax, soft_fail=True)

    logging.debug(f"  DEBUG: Cat info")
    if cat_info:
        if isinstance(cat_info, str):
            cats, cat_info = [cat_info], 1
            cat_text = f"{format_categories(cats, cat_info)}"
        else:
            cat_text = f"Categories: \n{format_categories(cats, cat_info)}"
        at = AnchoredText(
            cat_text,
            loc="upper left",
            pad=0.8,
            prop=dict(size="x-small", ha="center", linespacing=1.5),
            frameon=False,
        )
        ax.add_artist(at)
        hep.plot.yscale_anchored_text(ax, soft_fail=True)

    # Fit info
    if (chi2 or chi2_nocorr) and not blind:
        def chi2_calc(chi2_nocorr):
            # wrap to avoid global variables
            _chi2_tot, _chi2_naive_tot, _nbins = 0, 0, 0
            _chi2_cov_valid = True
            for channel in channels:
                data = getha("data", [channel], restoreNorm=restoreNorm)
                tot = getha("total", [channel], restoreNorm=restoreNorm)
                cov = geth("total_covar", channel, restoreNorm=False).values()
                mask = ~np.isclose(data.values(), 0, atol=1e-4)
                cov = cov[mask, :]
                cov = cov[:, mask]
                variances = data.variances()[mask]
                diff = data.values()[mask] - tot.values()[mask]
                chi2_naive = np.sum(np.nan_to_num(diff ** 2 / variances, posinf=0, neginf=0))
                _chi2_naive_tot += chi2_naive
                if not chi2_nocorr:
                    try:
                        chi2 = diff @ np.linalg.inv(cov+np.diag(variances)) @ diff
                        _chi2_tot += chi2
                    except np.linalg.LinAlgError:
                        _chi2_cov_valid = False
                        logging.warning(
                            "  Covariance matrix is singular. Will report naive chi2."
                        )
                _nbins += len(diff)
            logging.debug(f"  Chi2 ({cats[0]}): {_chi2_tot:.2f}")
            logging.debug(f"  Chi2 (naive) ({cats[0]}): {_chi2_naive_tot:.2f}")
            logging.debug(f"  Nbins ({cats[0]}): {_nbins:.0f}")
            if chi2_nocorr:
                return _chi2_naive_tot, _nbins, False
            else:
                return _chi2_tot, _nbins, _chi2_cov_valid
        chi2_val, _nbins, _chi2_cov_valid = chi2_calc(chi2_nocorr)

        if _chi2_cov_valid and not chi2_nocorr:
            _chi2_str = r"$\frac{\chi^2}{N_{bins}}$ = "
        else:
            _chi2_str = r"$\frac{\chi^2_{no~corr}}{N_{bins}}$ = "

        # Should be just a bit higher than 'saturated'
        at = AnchoredText(
            _chi2_str
            + r"$\frac{" + f"{chi2_val:.2f}" + r"}{" + f"{_nbins:.0f}" + r"}$",
            # r"}{N_{bins}}$ = "
            # + f"{chi2_val:.2f}/"
            # + f"{_nbins:.0f}",
            loc="upper left",  # pad=0.8,
            prop=dict(size="xx-small", ha="center"),
            frameon=False,
        )
        rax.add_artist(at)
        hep.plot.yscale_anchored_text(rax, soft_fail=True)

    ax.set_ylim(0, ax.get_ylim()[-1] * 1.05)

    if residuals and not blind:
        resid_unc = np.zeros_like(data.values())
        resid = data.values() - tot.values()
        logging.debug(f"  Residuals raw: {[f'{v:.2f}' for v in resid]}.")
        _lo, _hi = np.abs(
            hep.error_estimation.poisson_interval(data.values(), data.variances())
            - data.values()
        )
        resid_unc[resid < 0] = _hi[resid < 0]
        resid_unc[resid > 0] = _lo[resid > 0]
        resid /= resid_unc
        logging.debug(f"  Residuals: {[f'{v:.2f}' for v in resid]}.")
        resid = resid[~np.isclose(resid, 0, atol=1e-2)]
        logging.debug(f"  Residuals (filter zeros): {[f'{v:.2f}' for v in resid]}.")

        resid_ax = hep.append_axes(rax, size="26%", extend=False, pad=0.05)
        plt.subplots_adjust(wspace=0)
        xrange = np.linspace(-5, 5, 11)
        resid_ax.set_xlim(xrange[0], xrange[-1])
        resid_ax.set_xticks([-2, 0, 2])
        resid_ax.set_yticks([])
        resid_hist = hist.new.Var(xrange).Int64().fill(resid)
        resid_hist.plot(
            ax=resid_ax, yerr=False, density=False, flow="sum", lw=1.5, color="k"
        )
        hep.histplot(
            np.array([0.1, 2.1, 13.6, 34.1, 34.1, 13.6, 2.1, 0.1])
            * 0.01
            * resid_hist.sum(),
            bins=np.linspace(-4, 4, 9),
            ax=resid_ax,
            histtype="fill",
            color="gray",
            alpha=0.4,
        )
        resid_ax.set_xlabel("Residuals", ha="right", x=1)
        _stat, p_value = stats.shapiro(resid)
        _stat, p_value_ks = stats.kstest(resid, "norm", args=(0, np.std(resid)))

        anchored_text = AnchoredText(
            f"SW p-val = {p_value:.2f}\nKS p-val = {p_value_ks:.2f}",
            loc="upper left",
            frameon=False,
            prop=dict(size="xx-small"),
        )
        resid_ax.add_artist(anchored_text)

        resid_ax.set_ylim(
            resid_ax.get_ylim()[0]
            - ((resid_ax.get_ylim()[1] - (resid_ax.get_ylim()[0])) / 4),
            resid_ax.get_ylim()[1] * 1.5,
        )
        resid_ax.errorbar(
            resid, np.zeros_like(resid), yerr=0.01, fmt="|", markersize=4, c="k"
        )
        resid_ax.xaxis.minorticks_off()
        resid_ax.tick_params(top=False)
        hep.plot.yscale_anchored_text(resid_ax, soft_fail=True)

    logging.debug(f"  DEBUG: Main plotting done")
    return fig, (ax, rax)
