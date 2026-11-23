# ================================================================
# PGA ORD ITEM TYPE PAINTER - v0.24
#
# TWO-PASS ITEM TYPE WRITE BUILD
#
# PURPOSE
# -------
# Read all attached Item Types and primitive Item Type properties from one
# source element, display them in a PyQt5 UI, then graphically select target
# elements and copy the source metadata to those targets.
#
# v0.24 PYQT5 REVIEW DIALOG
# -------------------------
# The review, source pick, and target pick UI uses one persistent PyQt5
# dialog. Item Type rows have a 34-pixel size hint; property rows use 22 pixels.
# The MSPy picker and two-pass Item Type write path remain in place.
#
# v0.23 STANDARD TREE TEXT
# -----------------------
# Restore the original tree font and row height while keeping Apply after Value.
#
# v0.22 CHECKBOX LAYOUT
# ---------------------
# Show the Apply column to the right of Value and enlarge the Item Type rows
# so their checkboxes are easier to see and click.
#
# v0.21 ITEM TYPE SELECTION
# ------------------------
# Step 2 starts with every source Item Type selected. Users can toggle each
# Item Type before each target run. Only selected Item Types enter the
# assignment snapshot; the source snapshot remains intact for later runs.
#
# v0.20 MOVABLE DIALOG
# -------------------
# Add a visible drag handle and retain the user's window position when the
# dialog minimizes for source or target selection and then returns.
#
# v0.19 PERSISTENT DIALOG AND COMPACT LAYOUT
# -------------------------------------------
# Keep the review dialog's event loop running while the target picker
# collects elements. Minimize it during picking, then restore it after
# picker cleanup and the assignment result. The same source can be used
# for another target set, or re-picked in Step 1.
#
# FIELD-TEST HISTORY
# ------------------
# v0.18 proved the target DgnElementSetTool selection workflow stable:
#   - Source is read from MicroStation's normal Selection Set.
#   - The target picker is the first and only custom DgnElementSetTool.
#   - The target picker only collects IDs.
#   - EC/Item Type writes happen after picker cleanup.
#
# The remaining crash occurred when Item Types/property values were written.
#
# v0.18 therefore changes ONLY the EC write architecture:
#
#   1) Source property values are serialized to normal Python strings BEFORE
#      target selection using DgnECInstance.GetValueAsString().
#
#   2) No source ECInstance / ECValue / ItemType / EditElementHandle wrapper
#      is retained across the target-picker lifecycle.
#
#   3) ATTACH and UPDATE are separated into two native passes:
#
#        PASS A - ATTACH
#          - Fresh EditElementHandle
#          - Fresh CustomItemHost
#          - GetCustomItem()
#          - If missing: ApplyCustomItem()
#          - STOP. No SetValue()/WriteChanges() on the newly returned instance.
#
#        PASS B - UPDATE
#          - Re-fetch a fresh EditElementHandle
#          - Re-create CustomItemHost
#          - Re-fetch the now-existing Item Type instance
#          - SetValueAsString() for each transferable primitive property
#          - WriteChanges()
#
#      This mirrors Bentley's documented examples, where the attach example
#      performs ApplyCustomItem() by itself, and the update example starts
#      from an already-attached instance before changing values.
#
#   4) v0.18 does NOT pass an ECValue read from the source directly into a
#      target instance. ECValue is a C++ variant wrapper and is avoided in the
#      transfer path.
#
#   5) Every potentially dangerous native write step is flushed to:
#
#        %TEMP%\PGA_ORD_ItemTypePainter_v018.log
#
#      If MicroStation crashes, the final line in that log identifies the
#      native call reached immediately before the crash.
#
# v0.18 NATIVE-CRASH FIX
# ----------------------
# The v0.07 diagnostic log showed the native crash occurs inside
# CustomItemHost.ApplyCustomItem(). v0.18 corrects the Bentley wrapper
# lifetime around that call by retaining the owning ItemTypeLibrary object
# together with its child ItemType until ApplyCustomItem() returns.
# Explicit gc.collect() calls around Bentley wrappers were also removed.
#
# v0.18 COMPLETION / SELECTION-RESET UPDATE
# ------------------------------------------
# After Item Type/property assignment finishes:
#
#   - Every retained target element ID is added to MicroStation's REAL
#     SelectionSet.
#   - SelectionSetManager.BuildAgenda() materializes/highlights the complete
#     target set.
#   - SelectionSetManager.EmptyAll() immediately de-selects that complete set.
#
# This is the same proven select-then-de-select cleanup pattern used by
# PGA_ORD_ShoulderHatch_v022.py to clear stale locate highlighting.
#
# A modal completion dialog with an OK button is then displayed stating:
#
#     X Item Type(s) applied to Y element(s).
#
# The dialog is a standard Windows MessageBox so no second Tk mainloop is
# introduced after the MicroStation target tool has cleaned up.
#
# v0.18 COMPLETION-COUNT CORRECTION
# ---------------------------------
# v0.09 used assigned_count for the popup's element count. assigned_count
# means "all property writes completed without warnings", which is stricter
# than "the Item Types were successfully applied".
#
# A target can have all requested Item Types successfully attached/present
# and still be classified PARTIAL because one property value could not be
# written. That caused the completion popup to under-report target elements.
#
# v0.18 tracks Item Type application separately:
#
#   item_types_applied_element_ids
#
# An element enters that list after PASS A completes successfully for every
# requested Item Type, regardless of later property-level warnings.
#
# The completion dialog now reports:
#
#     X Item Type(s) applied to Y element(s).
#
# where Y is the number of targets that successfully completed the Item Type
# attach/presence pass. Property partial/failure counts remain available as
# separate diagnostics and do not reduce Y unless Item Type application itself
# failed.
#
# v0.18 UI SOURCE-PICK RESTORATION
# ---------------------------------
# v0.18 restores a "Pick / Re-Pick Source Element" button WITHOUT
# reintroducing a custom source DgnElementSetTool.
#
# This is critical because field testing proved that the downstream target
# workflow is most stable when ItemTypeTargetPickTool is the FIRST and ONLY
# custom DgnElementSetTool installed during the run.
#
# Source picking now uses MicroStation's ordinary SelectionSet:
#
#   1) User clicks "Pick / Re-Pick Source Element" in the Tk UI.
#   2) The current SelectionSet is emptied.
#   3) PyCommandState.StartDefaultCommand() returns MicroStation to its normal
#      default selection command.
#   4) The Tk UI remains alive and polls SelectionSetManager at a short
#      interval.
#   5) User graphically selects exactly ONE source element in MicroStation.
#   6) The UI detects the one-element SelectionSet automatically.
#   7) The source Item Types/properties are interrogated.
#   8) The source SelectionSet is cleared.
#   9) The UI refreshes with the source Element ID and Item Type tree.
#
# No custom Bentley locate tool is installed during source picking.
#
# Downstream target selection, Item Type attach/update, selection-set reset,
# completion accounting, popup notification, and native-crash diagnostics
# remain the proven v0.10 implementation.
#
# v0.18 SOURCE-PICK FIX
# ---------------------
# v0.11 used PyCommandState.StartDefaultCommand() when the source-pick button
# was pressed. That does not guarantee MicroStation's Element Selection tool
# becomes active.
#
# v0.18 explicitly starts MicroStation's native single-element selector with:
#
#     POWERSELECTOR MODE NEW;
#     POWERSELECTOR SINGLE;
#     CHOOSE ELEMENT
#
# The Tk dialog is temporarily minimized while the native selection is active.
# SelectionSet polling remains read-only and no custom source DgnElementSetTool
# is introduced. The proven target picker/write workflow is unchanged.
#
# v0.18 COOPERATIVE TK / MICROSTATION EVENT LOOP
# -----------------------------------------------
# Field testing established:
#
#   - v0.12: native CHOOSE ELEMENT was started, but Tk's mainloop prevented
#     MicroStation from processing the graphical source click.
#
#   - v0.17: GetInput successfully captured the source point, but replaying
#     that point with SendDataPoint crashed MicroStation.
#
# v0.18 removes GetInput/SendDataPoint/input replay completely.
#
# Bentley GUI samples demonstrate servicing MicroStation while an external
# Tk/PyQt event loop is active by periodically calling:
#
#     PyCadInputQueue.PythonMainLoop()
#
# v0.18 applies that pattern while the Tk review dialog is open.
#
# Source workflow:
#
#   1) Click "Pick / Re-Pick Source Element".
#   2) Clear the normal MicroStation SelectionSet.
#   3) Start native:
#
#          POWERSELECTOR MODE NEW;
#          POWERSELECTOR SINGLE;
#          CHOOSE ELEMENT
#
#   4) Tk continues running and periodically calls PythonMainLoop().
#   5) MicroStation itself consumes the user's graphical pick.
#   6) SelectionSetManager reports the selected source.
#   7) Source Item Types/properties are interrogated.
#   8) The source selection is cleared and the dialog refreshes.
#
# No source DgnElementSetTool is installed.
# No captured datapoint is replayed.
# Therefore the proven target DgnElementSetTool remains the first and only
# custom element-set tool installed by this script.
#
# Downstream target selection, EC writes, selection reset, completion counts,
# modal completion dialog, and write diagnostics remain unchanged from the
# proven v0.10-v0.12 implementation.
#
# SELECTION WORKFLOW
# ------------------
#   1) Select EXACTLY ONE source element with normal MicroStation Element
#      Selection before running this script.
#   2) Run the script and review the source Item Types/properties.
#   3) Click "Assign to Target Elements".
#   4) Data-point target elements repeatedly.
#   5) Reset/right-click accepts the target set.
#   6) The picker exits and fully cleans up.
#   7) v0.18 performs Pass A (attach missing Item Types).
#   8) v0.18 performs Pass B (update property values).
#
# ITEM TYPE COPY BEHAVIOR
# -----------------------
#   - Missing source Item Types are attached to each target.
#   - Existing matching Item Types are retained and updated.
#   - Unrelated target Item Types are preserved.
#   - The source itself is skipped if accidentally picked.
#   - Only primitive properties returned by ecClass.GetProperties(False) are
#     transferred in this version.
#
# TARGET SAFETY
# -------------
# v0.18 only writes to elements that can be re-found in the ACTIVE model and
# that report themselves as graphical elements. Reference-only/non-active
# targets are skipped rather than passed to CustomItemHost.
#
# DEPLOYMENT
# ----------
#   \Workspaces\PGA\Standards\Python
#
# ================================================================

from MSPyBentley import *
from MSPyECObjects import *
from MSPyDgnPlatform import *
from MSPyDgnView import *
from MSPyMstnPlatform import *

import ctypes
import os
import tempfile
import time
import sys
from PyQt5 import QtCore, QtWidgets


# ================================================================
# CONSTANTS
# ================================================================

SCRIPT_TITLE = "PGA Item Type Painter - v0.24"

TARGET_PICK_TOOL_ID = 9219

MAX_PROMPT_ERROR_LENGTH = 180

MICROSTATION_PUMP_MS = 20
SOURCE_SELECTION_POLL_MS = 120


_QT_APP = None


def get_qt_application():
    """Returns one QApplication for this ORD session."""
    global _QT_APP
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication(sys.argv[:1])
        _QT_APP = app
    app.setQuitOnLastWindowClosed(False)
    return app


# ================================================================
# BASIC MICROSTATION / UI HELPERS
# ================================================================

def _msg_error(title, text):
    try:
        MessageCenter.ShowErrorMessage(
            str(title),
            str(text),
            False,
        )
    except Exception:
        try:
            get_qt_application()
            QtWidgets.QMessageBox.critical(None, str(title), str(text))
        except Exception:
            print(f"{title}: {text}")


def _prompt(text):
    try:
        NotificationManager.OutputPrompt(
            str(text)
        )
    except Exception:
        print(text)


def _short_error(ex):
    text = str(ex).replace("\n", " ").strip()

    if len(text) > MAX_PROMPT_ERROR_LENGTH:
        text = (
            text[:MAX_PROMPT_ERROR_LENGTH - 3]
            +
            "..."
        )

    return text


def get_active_context():
    model_ref = ISessionMgr.ActiveDgnModelRef

    if model_ref is None:
        raise RuntimeError(
            "No active DGN model."
        )

    dgn_model = model_ref.GetDgnModel()
    dgn_file = model_ref.GetDgnFile()

    if dgn_model is None:
        raise RuntimeError(
            "Could not access the active DGN model."
        )

    if dgn_file is None:
        raise RuntimeError(
            "Could not access the active DGN file."
        )

    return (
        model_ref,
        dgn_model,
        dgn_file,
    )


def clear_picker_highlights(
    tool=None,
    clear_agenda=False,
):
    """
    Clear DgnElementSetTool agenda highlighting and the real SelectionSet.

    This mirrors the cleanup pattern proven in ShoulderHatch v0.22.
    """
    if tool is not None:

        try:
            agenda = tool.GetElementAgenda()
        except Exception:
            agenda = None

        if agenda is not None:

            try:
                clear_hilite = getattr(
                    agenda,
                    "ClearHilite",
                    None,
                )

                if callable(clear_hilite):
                    clear_hilite()

            except Exception:
                pass

            if clear_agenda:

                try:
                    clear_method = getattr(
                        agenda,
                        "Clear",
                        None,
                    )

                    if callable(clear_method):
                        clear_method()

                except Exception:
                    pass

    try:
        SelectionSetManager.GetManager().EmptyAll()
    except Exception:
        pass


def request_traditional_locate_cursor():
    """
    Request MicroStation's traditional locate cursor when this MSPy build
    exposes PyCommandState.SetLocateCursor().
    """
    try:
        set_cursor = getattr(
            PyCommandState,
            "SetLocateCursor",
            None,
        )

        if callable(set_cursor):
            set_cursor()
            return True

    except Exception:
        pass

    return False


def return_to_default_command():
    try:
        PyCommandState.StartDefaultCommand()
    except Exception:
        pass



def force_select_then_deselect_elements(
    element_ids,
):
    """
    Force the retained target elements through MicroStation's REAL
    SelectionSet and then remove them all.

    This intentionally follows the proven ShoulderHatch v0.22 pattern:

        EmptyAll()
        AddElement(...)
        BuildAgenda(...)
        EmptyAll()

    Returns the number of target elements successfully added before the
    final de-select.
    """
    if not element_ids:
        return 0

    (
        _model_ref,
        dgn_model,
        _dgn_file,
    ) = get_active_context()

    sel_mgr = SelectionSetManager.GetManager()

    try:
        sel_mgr.EmptyAll()
    except Exception:
        pass

    ordered_ids = []
    seen = set()

    for element_id in element_ids:

        try:
            element_id = int(
                element_id
            )
        except Exception:
            continue

        if element_id in seen:
            continue

        seen.add(
            element_id
        )

        ordered_ids.append(
            element_id
        )

    added = 0

    for element_id in ordered_ids:

        try:

            elem_ref = dgn_model.FindElementByID(
                element_id
            )

            if elem_ref is None:
                continue

            sel_mgr.AddElement(
                elem_ref,
                dgn_model,
            )

            added += 1

        except Exception as ex:

            _write_log(
                f"TARGET {element_id} | SELECTION RESET | "
                f"AddElement failed | {ex}"
            )

    if added > 0:

        try:

            agenda = ElementAgenda()

            sel_mgr.BuildAgenda(
                agenda
            )

            _write_log(
                f"SELECTION RESET | BuildAgenda count={agenda.GetCount()}"
            )

        except Exception as ex:

            _write_log(
                f"SELECTION RESET | BuildAgenda unavailable | {ex}"
            )

    try:

        sel_mgr.EmptyAll()

    except Exception as ex:

        _write_log(
            f"SELECTION RESET | final EmptyAll failed | {ex}"
        )

    _write_log(
        f"SELECTION RESET | select-then-deselect completed | "
        f"elements={added}"
    )

    return added


def show_completion_dialog(
    item_type_count,
    element_count,
    partial_count=0,
    failed_count=0,
):
    """
    Show a real modal popup with an OK button.

    Use the Windows MessageBox API without starting another GUI event loop
    from the post-tool cleanup callback.
    """
    item_type_count = int(
        item_type_count
    )

    element_count = int(
        element_count
    )

    partial_count = int(
        partial_count
    )

    failed_count = int(
        failed_count
    )

    message = (
        f"{item_type_count} Item Type(s) applied to "
        f"{element_count} element(s)."
    )

    try:

        MB_OK = 0x00000000
        MB_ICONINFORMATION = 0x00000040
        MB_SETFOREGROUND = 0x00010000

        ctypes.windll.user32.MessageBoxW(
            0,
            str(message),
            str(SCRIPT_TITLE),
            MB_OK
            |
            MB_ICONINFORMATION
            |
            MB_SETFOREGROUND,
        )

    except Exception:

        # Fallback only. Normal production path on Windows uses MessageBoxW.
        try:
            get_qt_application()
            QtWidgets.QMessageBox.information(None, SCRIPT_TITLE, message)
        except Exception:
            print(message)



def start_native_single_element_selection():
    """
    Start MicroStation's built-in Element Selection tool explicitly.

    Bentley documents:
        POWERSELECTOR MODE NEW
        POWERSELECTOR SINGLE
        CHOOSE ELEMENT

    Using the native selection command avoids installing a custom source
    DgnElementSetTool, so the proven target picker remains the first and only
    custom DgnElementSetTool installed by this script.
    """
    keyin = (
        "POWERSELECTOR MODE NEW;"
        "POWERSELECTOR SINGLE;"
        "CHOOSE ELEMENT"
    )

    _write_log(
        f"SOURCE PICK | sending native key-in | {keyin}"
    )

    PyCadInputQueue.SendKeyin(
        keyin
    )


def _api_result_failed(result):
    """
    Tolerate MSPy methods that return None on success while still detecting
    bool False / non-zero integer-like status values.
    """
    if result is None:
        return False

    if isinstance(result, bool):
        return not result

    try:
        return int(result) != 0
    except Exception:
        return False


# ================================================================
# ITEM TYPE / EC METADATA HELPERS
# ================================================================

WRITE_LOG_PATH = os.path.join(
    tempfile.gettempdir(),
    "PGA_ORD_ItemTypePainter_v024.log",
)


def _reset_write_log():
    try:
        with open(
            WRITE_LOG_PATH,
            "w",
            encoding="utf-8",
        ) as log:
            log.write(
                "PGA Item Type Painter v0.24 write log\n"
            )
            log.write(
                time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
                +
                "\n"
            )
            log.flush()
    except Exception:
        pass


def _write_log(text):
    """
    Flush every diagnostic line immediately. If MicroStation terminates in
    native code, the last line written shows the operation reached.
    """
    try:
        with open(
            WRITE_LOG_PATH,
            "a",
            encoding="utf-8",
        ) as log:
            log.write(
                str(text)
                +
                "\n"
            )
            log.flush()
    except Exception:
        pass


def _unique_nonempty_strings(values):
    result = []

    for value in values:

        if value is None:
            continue

        text = str(value).strip()

        if not text:
            continue

        if text not in result:
            result.append(
                text
            )

    return result


def _ec_name_candidates(ec_object):
    """
    Item Type APIs use display names, while EC instances also expose internal
    schema/class names. Retain both and resolve against ItemTypeLibrary.
    """
    values = []

    try:
        get_display_label = getattr(
            ec_object,
            "GetDisplayLabel",
            None,
        )

        if callable(
            get_display_label
        ):
            values.append(
                get_display_label()
            )

    except Exception:
        pass

    try:
        values.append(
            ec_object.GetName()
        )
    except Exception:
        pass

    return _unique_nonempty_strings(
        values
    )


def _ec_internal_name(ec_object):
    try:
        return str(
            ec_object.GetName()
        )
    except Exception:
        return ""


def get_custom_item_instances(eeh):
    """
    Known-good Bentley/PGA interrogation pattern.
    """
    host = CustomItemHost(
        eeh,
        False,
    )

    instances = DgnECInstanceVector()

    host.GetCustomItems(
        instances
    )

    return [
        instance
        for instance in instances
        if instance is not None
    ]


def resolve_item_type_names(
    instance,
    dgn_file,
):
    """
    Resolve the source EC schema/class to an Item Type Library + Item Type
    using names that ItemTypeLibrary actually accepts.
    """
    ec_class = (
        instance
        .GetEnabler()
        .GetClass()
    )

    ec_schema = (
        ec_class.GetSchema()
    )

    library_candidates = _ec_name_candidates(
        ec_schema
    )

    item_candidates = _ec_name_candidates(
        ec_class
    )

    for library_name in library_candidates:

        try:
            library = ItemTypeLibrary.FindByName(
                library_name,
                dgn_file,
            )
        except Exception:
            library = None

        if library is None:
            continue

        for item_name in item_candidates:

            try:
                item_type = library.GetItemTypeByName(
                    item_name
                )
            except Exception:
                item_type = None

            if item_type is not None:

                return {
                    "library_lookup_name":
                        library_name,
                    "item_lookup_name":
                        item_name,
                    "library_candidates":
                        library_candidates,
                    "item_candidates":
                        item_candidates,
                    "resolved":
                        True,
                }

    return {
        "library_lookup_name": (
            library_candidates[0]
            if library_candidates
            else ""
        ),
        "item_lookup_name": (
            item_candidates[0]
            if item_candidates
            else ""
        ),
        "library_candidates":
            library_candidates,
        "item_candidates":
            item_candidates,
        "resolved":
            False,
    }


def _get_value_as_transfer_string(
    instance,
    property_name,
):
    """
    Bentley's DgnECInstance exposes GetValueAsString/SetValueAsString.

    Use the string representation as the transfer boundary so no ECValue
    wrapper originating from the source is passed to the target instance.
    """
    text_value = WString()

    result = instance.GetValueAsString(
        text_value,
        property_name,
        False,
        0,
    )

    if _api_result_failed(
        result
    ):
        raise RuntimeError(
            f"GetValueAsString returned status {result}."
        )

    return str(
        text_value
    )


def read_primitive_property_rows(
    instance,
):
    """
    Read primitive properties and immediately serialize transferable values
    to plain Python strings.
    """
    ec_class = (
        instance
        .GetEnabler()
        .GetClass()
    )

    properties = ec_class.GetProperties(
        False
    )

    rows = []
    transfer_properties = []

    for primitive_prop in properties:

        try:
            property_name = str(
                primitive_prop.GetName()
            )
        except Exception:
            continue

        if not property_name:
            continue

        try:

            value_string = (
                _get_value_as_transfer_string(
                    instance,
                    property_name,
                )
            )

            transferable = True
            issue = ""

        except Exception as ex:

            # Display fallback only. This value is deliberately NOT copied.
            prop_value = ECValue()

            try:
                instance.GetValue(
                    prop_value,
                    property_name,
                )

                value_string = str(
                    prop_value.ToString()
                )

            except Exception:
                value_string = (
                    "<unreadable>"
                )

            transferable = False
            issue = _short_error(
                ex
            )

        rows.append(
            {
                "access":
                    property_name,
                "value":
                    value_string,
                "transferable":
                    transferable,
                "issue":
                    issue,
            }
        )

        transfer_properties.append(
            {
                "name":
                    property_name,
                "value_string":
                    value_string,
                "transferable":
                    transferable,
                "issue":
                    issue,
            }
        )

    return (
        transfer_properties,
        rows,
    )


def build_source_snapshot(eeh):
    """
    Produce a source snapshot containing ONLY Python primitive/container
    values. No Bentley EC objects survive beyond this function.
    """
    (
        _model_ref,
        _dgn_model,
        dgn_file,
    ) = get_active_context()

    source_id = int(
        eeh.GetElementId()
    )

    items = []

    instances = get_custom_item_instances(
        eeh
    )

    for instance in instances:

        ec_class = (
            instance
            .GetEnabler()
            .GetClass()
        )

        ec_schema = ec_class.GetSchema()

        schema_internal_name = (
            _ec_internal_name(
                ec_schema
            )
        )

        class_internal_name = (
            _ec_internal_name(
                ec_class
            )
        )

        resolved = resolve_item_type_names(
            instance,
            dgn_file,
        )

        (
            transfer_properties,
            display_rows,
        ) = read_primitive_property_rows(
            instance
        )

        items.append(
            {
                "schema_internal_name":
                    schema_internal_name,
                "class_internal_name":
                    class_internal_name,
                "library_candidates":
                    list(
                        resolved[
                            "library_candidates"
                        ]
                    ),
                "item_candidates":
                    list(
                        resolved[
                            "item_candidates"
                        ]
                    ),
                "library_lookup_name":
                    resolved[
                        "library_lookup_name"
                    ],
                "item_lookup_name":
                    resolved[
                        "item_lookup_name"
                    ],
                "display_library": (
                    resolved[
                        "library_lookup_name"
                    ]
                    if resolved[
                        "library_lookup_name"
                    ]
                    else (
                        schema_internal_name
                        if schema_internal_name
                        else "(unknown library)"
                    )
                ),
                "display_item": (
                    resolved[
                        "item_lookup_name"
                    ]
                    if resolved[
                        "item_lookup_name"
                    ]
                    else (
                        class_internal_name
                        if class_internal_name
                        else "(unknown Item Type)"
                    )
                ),
                "properties":
                    transfer_properties,
                "display_rows":
                    display_rows,
                "ready":
                    bool(
                        resolved[
                            "resolved"
                        ]
                    ),
            }
        )

    # Drop source EC wrappers before the UI/target-tool lifecycle begins.
    instances = None

    return {
        "source_element_id":
            source_id,
        "items":
            items,
    }


def source_snapshot_is_assignable(
    snapshot,
):
    if not snapshot:
        return False

    items = snapshot.get(
        "items",
        [],
    )

    if not items:
        return False

    return all(
        bool(
            item.get(
                "ready"
            )
        )
        for item in items
    )


def _resolve_item_type_definition_fresh(
    item_snapshot,
    dgn_file,
):
    """
    Resolve the Item Type and KEEP its owning ItemTypeLibrary wrapper alive.

    Bentley's working Python examples retain the library object in scope
    while passing a child ItemType to CustomItemHost.ApplyCustomItem().
    """
    library_candidates = (
        item_snapshot.get("library_candidates", [])
        or [item_snapshot.get("library_lookup_name", "")]
    )

    item_candidates = (
        item_snapshot.get("item_candidates", [])
        or [item_snapshot.get("item_lookup_name", "")]
    )

    for library_name in library_candidates:
        if not library_name:
            continue

        try:
            library = ItemTypeLibrary.FindByName(
                library_name,
                dgn_file,
            )
        except Exception:
            library = None

        if library is None:
            continue

        for item_name in item_candidates:
            if not item_name:
                continue

            try:
                item_type = library.GetItemTypeByName(
                    item_name
                )
            except Exception:
                item_type = None

            if item_type is not None:
                return (
                    library_name,
                    item_name,
                    library,
                    item_type,
                )

    return (
        None,
        None,
        None,
        None,
    )


def _fresh_target_handle(
    target_id,
    dgn_model,
):
    """
    Obtain a completely fresh active-model EditElementHandle.
    """
    target_ref = dgn_model.FindElementByID(
        int(
            target_id
        )
    )

    if target_ref is None:
        raise RuntimeError(
            "Element was not found in the active model."
        )

    eeh = EditElementHandle(
        target_ref,
        dgn_model,
    )

    try:
        if not eeh.IsValid():
            raise RuntimeError(
                "Target EditElementHandle is invalid."
            )
    except AttributeError:
        pass

    return eeh


def _validate_target_for_custom_item_write(
    target_id,
    dgn_model,
):
    """
    Bentley's published Python Item Type attach/update examples operate on
    normal graphical elements. Avoid sending non-graphical targets into
    CustomItemHost.
    """
    eeh = _fresh_target_handle(
        target_id,
        dgn_model,
    )

    ms_element = eeh.GetElement()

    if ms_element is None:
        raise RuntimeError(
            "Could not read target element data."
        )

    try:
        if not bool(
            ms_element.ehdr.isGraphics
        ):
            raise RuntimeError(
                "Target is not a graphical element."
            )
    except AttributeError:
        # If this build does not expose the legacy header flags, do not invent
        # another test; continue with the valid active-model handle.
        pass

    return True


def _attach_missing_item_to_target(
    target_id,
    item_snapshot,
    dgn_model,
    dgn_file,
):
    """
    PASS A - attach only.

    v0.18 keeps all related Bentley wrapper objects strongly referenced
    through ApplyCustomItem():
        dgn_file -> item_library -> item_type
        dgn_model -> eeh -> host
    """
    (
        library_name,
        item_name,
        item_library,
        item_type,
    ) = _resolve_item_type_definition_fresh(
        item_snapshot,
        dgn_file,
    )

    if item_library is None or item_type is None:
        raise RuntimeError(
            "Could not resolve Item Type definition "
            f"'{item_snapshot.get('display_item', '')}' "
            f"in library '{item_snapshot.get('display_library', '')}'."
        )

    eeh = _fresh_target_handle(
        target_id,
        dgn_model,
    )

    try:
        element_type = int(
            eeh.GetElementType()
        )
    except Exception:
        element_type = -1

    _write_log(
        f"TARGET {target_id} | ATTACH | element_type={element_type} | "
        f"library_wrapper_alive={item_library is not None} | "
        f"itemtype_wrapper_alive={item_type is not None}"
    )

    _write_log(
        f"TARGET {target_id} | ATTACH | before CustomItemHost | "
        f"{library_name}.{item_name}"
    )

    host = CustomItemHost(
        eeh,
        False,
    )

    _write_log(
        f"TARGET {target_id} | ATTACH | after CustomItemHost | "
        f"{library_name}.{item_name}"
    )

    existing = host.GetCustomItem(
        library_name,
        item_name,
    )

    _write_log(
        f"TARGET {target_id} | ATTACH | after GetCustomItem | "
        f"{library_name}.{item_name} | found={existing is not None}"
    )

    if existing is not None:
        _write_log(
            f"TARGET {target_id} | ATTACH | already exists | "
            f"{library_name}.{item_name}"
        )
        return False

    _write_log(
        f"TARGET {target_id} | ATTACH | BEFORE ApplyCustomItem | "
        f"{library_name}.{item_name} | "
        f"element_type={element_type} | "
        f"library_wrapper_alive={item_library is not None}"
    )

    # Do not release item_library or item_type before this native call.
    attached_instance = host.ApplyCustomItem(
        item_type
    )

    _write_log(
        f"TARGET {target_id} | ATTACH | AFTER ApplyCustomItem | "
        f"{library_name}.{item_name} | "
        f"instance_returned={attached_instance is not None}"
    )

    if attached_instance is None:
        raise RuntimeError(
            f"ApplyCustomItem returned None for "
            f"{library_name}.{item_name}."
        )

    # Property changes are intentionally deferred to Pass B.
    return True


def _update_existing_item_on_target(
    target_id,
    item_snapshot,
    dgn_model,
):
    """
    PASS B.

    Re-open the target and its now-existing Item Type instance. Transfer each
    primitive property using SetValueAsString, then call WriteChanges once.
    """
    library_name = item_snapshot.get(
        "library_lookup_name",
        "",
    )

    item_name = item_snapshot.get(
        "item_lookup_name",
        "",
    )

    if (
        not library_name
        or
        not item_name
    ):
        raise RuntimeError(
            "Resolved Item Type names are missing."
        )

    eeh = _fresh_target_handle(
        target_id,
        dgn_model,
    )

    _write_log(
        f"TARGET {target_id} | UPDATE | before CustomItemHost | "
        f"{library_name}.{item_name}"
    )

    host = CustomItemHost(
        eeh,
        False,
    )

    _write_log(
        f"TARGET {target_id} | UPDATE | after CustomItemHost | "
        f"{library_name}.{item_name}"
    )

    instance = host.GetCustomItem(
        library_name,
        item_name,
    )

    _write_log(
        f"TARGET {target_id} | UPDATE | after GetCustomItem | "
        f"{library_name}.{item_name} | "
        f"found={instance is not None}"
    )

    if instance is None:
        raise RuntimeError(
            f"Item Type {library_name}.{item_name} was not found "
            "after the attach pass."
        )

    failures = []
    copied = 0
    attempted = 0

    for prop in item_snapshot.get(
        "properties",
        [],
    ):

        property_name = prop.get(
            "name",
            "",
        )

        if not property_name:
            continue

        if not prop.get(
            "transferable",
            False,
        ):

            failures.append(
                (
                    property_name,
                    "Source GetValueAsString was unavailable: "
                    +
                    prop.get(
                        "issue",
                        "",
                    ),
                )
            )

            continue

        value_string = str(
            prop.get(
                "value_string",
                "",
            )
        )

        attempted += 1

        _write_log(
            f"TARGET {target_id} | UPDATE | BEFORE SetValueAsString | "
            f"{library_name}.{item_name}.{property_name} | "
            f"value={value_string!r}"
        )

        try:

            result = instance.SetValueAsString(
                property_name,
                value_string,
                False,
                0,
            )

        except Exception as ex:

            failures.append(
                (
                    property_name,
                    "SetValueAsString exception: "
                    +
                    str(ex),
                )
            )

            _write_log(
                f"TARGET {target_id} | UPDATE | SetValueAsString EXCEPTION | "
                f"{library_name}.{item_name}.{property_name} | {ex}"
            )

            continue

        _write_log(
            f"TARGET {target_id} | UPDATE | AFTER SetValueAsString | "
            f"{library_name}.{item_name}.{property_name} | status={result}"
        )

        if _api_result_failed(
            result
        ):

            failures.append(
                (
                    property_name,
                    f"SetValueAsString returned status {result}.",
                )
            )

        else:
            copied += 1

    if attempted > 0:

        _write_log(
            f"TARGET {target_id} | UPDATE | BEFORE WriteChanges | "
            f"{library_name}.{item_name}"
        )

        try:

            write_result = instance.WriteChanges()

        except Exception as ex:

            failures.append(
                (
                    "(WriteChanges)",
                    str(ex),
                )
            )

            _write_log(
                f"TARGET {target_id} | UPDATE | WriteChanges EXCEPTION | "
                f"{library_name}.{item_name} | {ex}"
            )

        else:

            _write_log(
                f"TARGET {target_id} | UPDATE | AFTER WriteChanges | "
                f"{library_name}.{item_name} | status={write_result}"
            )

            if _api_result_failed(
                write_result
            ):

                failures.append(
                    (
                        "(WriteChanges)",
                        f"WriteChanges returned status {write_result}.",
                    )
                )

    instance = None
    host = None
    eeh = None

    return {
        "library":
            library_name,
        "item":
            item_name,
        "properties_copied":
            copied,
        "property_failures":
            failures,
    }


def apply_snapshot_to_target_ids(
    snapshot,
    target_ids,
):
    """
    Apply metadata only after target-picker cleanup.

    Native write sequence:
        A) attach missing Item Types to all targets
        B) reopen fresh handles and update values
    """
    if not source_snapshot_is_assignable(
        snapshot
    ):
        raise RuntimeError(
            "The source snapshot is not ready for assignment."
        )

    (
        _model_ref,
        dgn_model,
        dgn_file,
    ) = get_active_context()

    source_id = int(
        snapshot[
            "source_element_id"
        ]
    )

    ordered_target_ids = []
    seen = set()
    skipped_source = 0

    for target_id in target_ids:

        try:
            target_id = int(
                target_id
            )
        except Exception:
            continue

        if target_id == source_id:

            skipped_source += 1
            continue

        if target_id in seen:
            continue

        seen.add(
            target_id
        )

        ordered_target_ids.append(
            target_id
        )

    _reset_write_log()

    _write_log(
        f"BEGIN ASSIGNMENT | source={source_id} | targets={ordered_target_ids}"
    )

    summary = {
        "requested_count":
            len(
                ordered_target_ids
            ),
        "assigned_count":
            0,
        "partial_count":
            0,
        "failed_count":
            0,
        "skipped_source_count":
            skipped_source,
        "source_item_type_count":
            len(
                snapshot.get(
                    "items",
                    [],
                )
            ),
        "target_element_ids":
            list(
                ordered_target_ids
            ),
        "item_types_applied_element_ids":
            [],
        "item_types_applied_element_count":
            0,
        "details":
            [],
        "log_path":
            WRITE_LOG_PATH,
    }

    # ------------------------------------------------------------
    # PRE-FLIGHT
    # ------------------------------------------------------------

    valid_target_ids = []

    for target_id in ordered_target_ids:

        try:

            _write_log(
                f"TARGET {target_id} | PREFLIGHT | begin"
            )

            _validate_target_for_custom_item_write(
                target_id,
                dgn_model,
            )

            _write_log(
                f"TARGET {target_id} | PREFLIGHT | passed"
            )

            valid_target_ids.append(
                target_id
            )

        except Exception as ex:

            summary[
                "failed_count"
            ] += 1

            summary[
                "details"
            ].append(
                {
                    "target_id":
                        target_id,
                    "status":
                        "failed",
                    "issues":
                        [
                            (
                                "(preflight)",
                                str(ex),
                            )
                        ],
                }
            )

            _write_log(
                f"TARGET {target_id} | PREFLIGHT | failed | {ex}"
            )

    # ------------------------------------------------------------
    # PASS A - ATTACH MISSING ITEM TYPES ONLY
    # ------------------------------------------------------------

    attach_failed_targets = set()

    for target_id in valid_target_ids:

        _prompt(
            f"Item Type Painter: Preparing target {target_id}..."
        )

        for item_snapshot in snapshot[
            "items"
        ]:

            try:

                _attach_missing_item_to_target(
                    target_id,
                    item_snapshot,
                    dgn_model,
                    dgn_file,
                )

            except Exception as ex:

                attach_failed_targets.add(
                    target_id
                )

                _write_log(
                    f"TARGET {target_id} | ATTACH | Python exception | {ex}"
                )

                summary[
                    "details"
                ].append(
                    {
                        "target_id":
                            target_id,
                        "status":
                            "failed",
                        "issues":
                            [
                                (
                                    "(attach)",
                                    str(ex),
                                )
                            ],
                    }
                )

                break

    # ------------------------------------------------------------
    # ITEM TYPE APPLICATION ACCOUNTING
    #
    # A target is counted here once PASS A completed without an attach error.
    # This is intentionally independent of later property-level warnings.
    # ------------------------------------------------------------

    item_types_applied_element_ids = [
        target_id
        for target_id in valid_target_ids
        if target_id not in attach_failed_targets
    ]

    summary[
        "item_types_applied_element_ids"
    ] = list(
        item_types_applied_element_ids
    )

    summary[
        "item_types_applied_element_count"
    ] = len(
        item_types_applied_element_ids
    )

    _write_log(
        "ITEM TYPE APPLICATION | "
        f"elements={summary['item_types_applied_element_count']} | "
        f"ids={item_types_applied_element_ids}"
    )

    # ------------------------------------------------------------
    # PASS B - REOPEN + UPDATE VALUES
    # ------------------------------------------------------------

    for target_id in valid_target_ids:

        if target_id in attach_failed_targets:

            summary[
                "failed_count"
            ] += 1

            continue

        target_issues = []
        total_properties = 0

        for item_snapshot in snapshot[
            "items"
        ]:

            try:

                result = _update_existing_item_on_target(
                    target_id,
                    item_snapshot,
                    dgn_model,
                )

                total_properties += int(
                    result[
                        "properties_copied"
                    ]
                )

                for (
                    prop_name,
                    issue,
                ) in result[
                    "property_failures"
                ]:

                    target_issues.append(
                        (
                            f"{result['library']}."
                            f"{result['item']}."
                            f"{prop_name}",
                            issue,
                        )
                    )

            except Exception as ex:

                target_issues.append(
                    (
                        "(update)",
                        str(ex),
                    )
                )

                _write_log(
                    f"TARGET {target_id} | UPDATE | Python exception | {ex}"
                )

        if target_issues:

            summary[
                "partial_count"
            ] += 1

            status = "partial"

            _prompt(
                f"Item Type Painter: Target {target_id} updated PARTIALLY; "
                f"{len(target_issues)} issue(s)."
            )

        else:

            summary[
                "assigned_count"
            ] += 1

            status = "success"

            _prompt(
                f"Item Type Painter: Target {target_id} updated; "
                f"{total_properties} property value(s) copied."
            )

        summary[
            "details"
        ].append(
            {
                "target_id":
                    target_id,
                "status":
                    status,
                "issues":
                    target_issues,
            }
        )

    _write_log(
        "END ASSIGNMENT | "
        f"item_types_applied_elements="
        f"{summary['item_types_applied_element_count']} | "
        f"property_complete={summary['assigned_count']} | "
        f"property_partial={summary['partial_count']} | "
        f"failed={summary['failed_count']}"
    )

    return summary


# ================================================================
# SOURCE FROM NORMAL MICROSTATION SELECTION SET
# ================================================================

def get_source_snapshot_from_selection():
    """
    Read exactly one element from MicroStation's real SelectionSet.

    v0.18 intentionally uses the ordinary SelectionSet for SOURCE selection.
    No custom source DgnElementSetTool is installed, preserving the proven
    downstream target-tool lifecycle.
    """
    sel_mgr = SelectionSetManager.GetManager()

    count = int(
        sel_mgr.NumSelected()
    )

    if count <= 0:
        raise RuntimeError(
            "No source element is selected."
        )

    if count != 1:
        raise RuntimeError(
            f"{count} elements are selected. "
            "Select exactly ONE source element."
        )

    eeh = EditElementHandle()

    sel_mgr.GetElement(
        0,
        eeh,
    )

    try:
        if not eeh.IsValid():
            raise RuntimeError(
                "MicroStation returned an invalid source element handle."
            )
    except AttributeError:
        pass

    return build_source_snapshot(
        eeh
    )



# ================================================================
# TARGET PICK TOOL
# ================================================================

class ItemTypeTargetPickTool(DgnElementSetTool):
    """
    SAFE TARGET PICKER.

    This class NEVER writes Item Types and NEVER modifies target elements.

    It only accumulates target IDs in the native ElementAgenda. On Reset,
    those IDs are copied into normal Python integers. The tool then exits.
    The session applies Item Types only after _OnCleanup has completed.
    """

    s_instance = None

    def __init__(
        self,
        tool_id,
        source_element_id,
        on_complete,
        on_abort,
    ):
        DgnElementSetTool.__init__(
            self,
            tool_id,
        )

        self.source_element_id = int(
            source_element_id
        )

        self.on_complete = on_complete
        self.on_abort = on_abort

        self._pending_target_ids = []
        self._normal_finish = False
        self._cleanup_seen = False

        self.m_self = self


    def _GetToolName(
        self,
        name,
    ):
        return WString(
            "PGA Item Type Painter - Pick Targets"
        )


    def _OnPostInstall(self):

        AccuSnap.GetInstance().EnableSnap(
            True
        )

        DgnElementSetTool._OnPostInstall(
            self
        )

        request_traditional_locate_cursor()

        _prompt(
            "Item Type Painter: Pick TARGET elements. "
            "Data-point = add target. "
            "Reset/right-click = accept targets and apply Item Types. "
            "ESC = cancel."
        )


    def _WantDynamics(self):
        return False


    def _NeedAcceptPoint(self):
        return True


    def _WantAdditionalLocate(
        self,
        ev,
    ):
        """
        Keep accumulating native locate results.

        IMPORTANT:
        Do not dereference agenda entries here.
        Do not modify EC data here.
        Do not clear the agenda here.
        """
        try:
            agenda = self.GetElementAgenda()

            if agenda is not None:

                count = int(
                    agenda.GetCount()
                )

                if count > 0:

                    _prompt(
                        f"Item Type Painter: {count} target pick(s) queued. "
                        "Continue picking or Reset/right-click to apply."
                    )

        except Exception:
            pass

        request_traditional_locate_cursor()

        return True


    def _OnPostLocate(
        self,
        path,
        cantAcceptReason,
    ):
        try:
            return bool(
                DgnElementSetTool._OnPostLocate(
                    self,
                    path,
                    cantAcceptReason,
                )
            )
        except Exception:
            return path is not None


    def _read_target_ids_from_agenda(
        self,
    ):
        """
        Read IDs only at explicit Reset/accept time, matching the
        ShoulderHatch selection/accept pattern.
        """
        agenda = self.GetElementAgenda()

        if agenda is None:
            return []

        target_ids = []
        seen = set()

        total = int(
            agenda.GetCount()
        )

        for i in range(
            total
        ):

            eeh = agenda.GetEntry(
                i
            )

            if eeh is None:
                continue

            try:
                if not eeh.IsValid():
                    continue
            except Exception:
                pass

            target_id = int(
                eeh.GetElementId()
            )

            if target_id == self.source_element_id:
                continue

            if target_id in seen:
                continue

            seen.add(
                target_id
            )

            target_ids.append(
                target_id
            )

        return target_ids


    def _OnResetButton(
        self,
        ev,
    ):
        """
        Accept the target set. NO target modification occurs here.
        """
        try:

            self._pending_target_ids = (
                self._read_target_ids_from_agenda()
            )

        except Exception as ex:

            _prompt(
                "Item Type Painter: Could not read target selection - "
                +
                _short_error(ex)
            )

            return True

        self._normal_finish = True

        _prompt(
            f"Item Type Painter: "
            f"{len(self._pending_target_ids)} target(s) accepted. "
            "Exiting target picker before applying Item Types."
        )

        try:
            self._ExitTool()
        except Exception:
            return_to_default_command()

        return True


    def _OnCleanup(self):

        if self._cleanup_seen:
            return

        self._cleanup_seen = True

        normal_finish = bool(
            self._normal_finish
        )

        target_ids = list(
            self._pending_target_ids
        )

        complete_callback = (
            self.on_complete
        )

        abort_callback = (
            self.on_abort
        )

        if ItemTypeTargetPickTool.s_instance is self:
            ItemTypeTargetPickTool.s_instance = None

        # First remove agenda highlighting while the agenda still exists.
        clear_picker_highlights(
            self,
            clear_agenda=True,
        )

        # Then let Bentley complete native tool cleanup.
        try:
            DgnElementSetTool._OnCleanup(
                self
            )
        except Exception:
            pass

        # Base cleanup can touch command/selection state; normalize once more.
        clear_picker_highlights(
            None
        )

        return_to_default_command()

        # ONLY NOW is the session callback allowed to modify targets.
        if normal_finish:

            try:
                complete_callback(
                    target_ids
                )
            except Exception as ex:
                _msg_error(SCRIPT_TITLE, ex)
                complete_callback.__self__.on_callback_failure(ex)

            return

        try:
            abort_callback()
        except Exception as ex:
            _msg_error(SCRIPT_TITLE, ex)
            abort_callback.__self__.on_callback_failure(ex)


    def _OnRestartTool(self):
        return


    @staticmethod
    def InstallNewInstance(
        tool_id,
        source_element_id,
        on_complete,
        on_abort,
    ):

        tool = ItemTypeTargetPickTool(
            tool_id,
            source_element_id,
            on_complete,
            on_abort,
        )

        ItemTypeTargetPickTool.s_instance = tool

        tool.InstallTool()




# ================================================================
# PYQT5 REVIEW UI
# ================================================================

class ItemTypePainterDialog(QtWidgets.QDialog):
    """Persistent PyQt5 review dialog for source and target selection."""

    def __init__(self, source_snapshot=None):
        get_qt_application()
        super().__init__(None)
        self.source_snapshot = source_snapshot
        self.source_pick_active = False
        self.target_pick_active = False
        self.dialog_closed = False
        self.selected_item_indices = set()
        self._last_source_selection_count = None
        self._saved_position = None
        self._event_loop = None
        self._loading_tree = False

        self.setWindowTitle(SCRIPT_TITLE)
        self.setWindowFlag(QtCore.Qt.WindowContextHelpButtonHint, False)
        self.setMinimumSize(630, 500)
        self.resize(680, 620)

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        source_group = QtWidgets.QGroupBox("Step 1. Select Source Element")
        source_layout = QtWidgets.QGridLayout(source_group)
        source_layout.addWidget(QtWidgets.QLabel("Element ID:"), 0, 0)
        self.source_id_label = QtWidgets.QLabel("None")
        source_font = self.source_id_label.font()
        source_font.setBold(True)
        self.source_id_label.setFont(source_font)
        source_layout.addWidget(self.source_id_label, 0, 1)
        source_layout.setColumnStretch(1, 1)
        self.source_button = QtWidgets.QPushButton("Select Source Element")
        self.source_button.clicked.connect(self.toggle_source_pick)
        source_layout.addWidget(self.source_button, 0, 2)
        source_hint = QtWidgets.QLabel(
            "Click the button, then select exactly one source element in MicroStation/OpenRoads."
        )
        source_hint.setWordWrap(True)
        source_layout.addWidget(source_hint, 1, 0, 1, 3)
        outer.addWidget(source_group)

        property_group = QtWidgets.QGroupBox("Step 2. Select Item Types and Verify Values")
        property_layout = QtWidgets.QVBoxLayout(property_group)
        selection_bar = QtWidgets.QHBoxLayout()
        selection_bar.addWidget(QtWidgets.QLabel(
            "Toggle an 'Apply' checkbox to include or exclude an Item Type."
        ))
        selection_bar.addStretch(1)
        select_all_button = QtWidgets.QPushButton("Select all")
        select_all_button.clicked.connect(self.select_all_item_types)
        selection_bar.addWidget(select_all_button)
        clear_all_button = QtWidgets.QPushButton("Clear all")
        clear_all_button.clicked.connect(self.clear_all_item_types)
        selection_bar.addWidget(clear_all_button)
        property_layout.addLayout(selection_bar)

        self.tree = QtWidgets.QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(["Item Type / Property", "Value", "Apply"])
        self.tree.setColumnWidth(0, 300)
        self.tree.setColumnWidth(1, 200)
        self.tree.setColumnWidth(2, 75)
        self.tree.setUniformRowHeights(False)
        self.tree.setRootIsDecorated(True)
        self.tree.itemChanged.connect(self._on_item_changed)
        property_layout.addWidget(self.tree, 1)
        outer.addWidget(property_group, 1)

        assign_group = QtWidgets.QGroupBox(
            "Step 3. Assign Item Types and Values to Other Elements"
        )
        assign_layout = QtWidgets.QHBoxLayout(assign_group)
        instruction = QtWidgets.QLabel(
            "Click 'Assign to Target Elements'.<br>"
            "Select one or more elements (Left-click).<br>"
            "Reset (Right-click) to accept."
        )
        instruction.setWordWrap(True)
        assign_layout.addWidget(instruction, 1)
        self.assign_button = QtWidgets.QPushButton("Assign to Target Elements")
        self.assign_button.clicked.connect(self.assign_targets)
        assign_layout.addWidget(self.assign_button)
        outer.addWidget(assign_group)

        footer = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel()
        self.status_label.setWordWrap(True)
        footer.addWidget(self.status_label, 1)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.close)
        footer.addWidget(close_button)
        outer.addLayout(footer)

        self._pump_timer = QtCore.QTimer(self)
        self._pump_timer.setInterval(MICROSTATION_PUMP_MS)
        self._pump_timer.timeout.connect(self._pump_microstation_once)
        self._source_timer = QtCore.QTimer(self)
        self._source_timer.setInterval(SOURCE_SELECTION_POLL_MS)
        self._source_timer.timeout.connect(self._poll_source_selection)
        self.refresh_source_display()

    def _selected_snapshot(self):
        """Returns only the selected Item Types for one target run."""
        if not self.source_snapshot:
            return None
        items = self.source_snapshot.get("items", [])
        return {
            "source_element_id": self.source_snapshot["source_element_id"],
            "items": [item for index, item in enumerate(items)
                      if index in self.selected_item_indices],
        }

    def _update_item_type_selection(self, update_status=True):
        """Keeps the checkboxes, button, and status aligned with the selection."""
        self._loading_tree = True
        try:
            for index in range(self.tree.topLevelItemCount()):
                row = self.tree.topLevelItem(index)
                if row.data(0, QtCore.Qt.UserRole) is None:
                    continue
                state = (QtCore.Qt.Checked if index in self.selected_item_indices
                         else QtCore.Qt.Unchecked)
                row.setCheckState(2, state)
        finally:
            self._loading_tree = False
        ready = source_snapshot_is_assignable(self._selected_snapshot())
        self.assign_button.setEnabled(
            ready and not self.source_pick_active and not self.target_pick_active
        )
        if not update_status or not self.source_snapshot:
            return
        selected = len(self.selected_item_indices)
        total = len(self.source_snapshot.get("items", []))
        if selected == 0:
            self.status_label.setText("Toggle on at least one Item Type.")
        elif not ready:
            self.status_label.setText(
                "A selected Item Type could not be resolved. Clear its Apply box to continue."
            )
        else:
            self.status_label.setText(
                f"Ready: {selected} of {total} Item Type(s) selected for assignment."
            )

    def _on_item_changed(self, row, column):
        """Updates the selected Item Types when an Apply box changes."""
        if self._loading_tree or column != 2:
            return
        index = row.data(0, QtCore.Qt.UserRole)
        if index is None:
            return
        if self.source_pick_active or self.target_pick_active:
            self._update_item_type_selection(update_status=False)
            return
        if row.checkState(2) == QtCore.Qt.Checked:
            self.selected_item_indices.add(index)
        else:
            self.selected_item_indices.discard(index)
        self._update_item_type_selection()

    def select_all_item_types(self):
        """Selects every Item Type on the current source element."""
        if self.source_pick_active or self.target_pick_active or not self.source_snapshot:
            return
        self.selected_item_indices = set(range(len(self.source_snapshot.get("items", []))))
        self._update_item_type_selection()

    def clear_all_item_types(self):
        """Clears every Item Type selection on the current source element."""
        if self.source_pick_active or self.target_pick_active:
            return
        self.selected_item_indices.clear()
        self._update_item_type_selection()

    def refresh_source_display(self):
        """Shows the current source, with all its Item Types selected."""
        self._loading_tree = True
        self.tree.clear()
        self.selected_item_indices.clear()
        snapshot = self.source_snapshot
        if not snapshot:
            self.source_id_label.setText("None")
            QtWidgets.QTreeWidgetItem(self.tree, ["(No source element selected)", "", ""])
            self.assign_button.setEnabled(False)
            self.status_label.setText(
                "Click 'Select Source Element', then select one source element in MicroStation."
            )
            self._loading_tree = False
            return

        self.source_id_label.setText(str(snapshot.get("source_element_id", "Unknown")))
        items = snapshot.get("items", [])
        self.selected_item_indices = set(range(len(items)))
        if not items:
            QtWidgets.QTreeWidgetItem(
                self.tree, ["(No Item Types attached to source element)", "", ""]
            )
            self.assign_button.setEnabled(False)
            self.status_label.setText("The selected source has no attached Item Types.")
            self._loading_tree = False
            return

        for index, item in enumerate(items):
            name = (
                f"{item.get('display_item', '(unknown Item Type)')} "
                f"[{item.get('display_library', '(unknown library)')}]"
            )
            parent = QtWidgets.QTreeWidgetItem(self.tree, [name, "", ""])
            parent.setFlags(parent.flags() | QtCore.Qt.ItemIsUserCheckable)
            parent.setCheckState(2, QtCore.Qt.Checked)
            parent.setSizeHint(0, QtCore.QSize(0, 34))
            parent.setExpanded(True)
            parent.setData(0, QtCore.Qt.UserRole, index)
            rows = item.get("display_rows", [])
            if not rows:
                child = QtWidgets.QTreeWidgetItem(parent, ["(No primitive properties)", "", ""])
                child.setSizeHint(0, QtCore.QSize(0, 22))
            else:
                for row in rows:
                    child = QtWidgets.QTreeWidgetItem(
                        parent,
                        [str(row.get("access", "(unnamed property)")),
                         str(row.get("value", "")), ""],
                    )
                    child.setSizeHint(0, QtCore.QSize(0, 22))
            if not item.get("ready"):
                child = QtWidgets.QTreeWidgetItem(
                    parent,
                    ["Assignment preparation issue",
                     "Item Type definition could not be resolved in the active DGN file.", ""],
                )
                child.setSizeHint(0, QtCore.QSize(0, 22))
        self._loading_tree = False
        self._update_item_type_selection()

    def _pump_microstation_once(self):
        """Services native MicroStation input while the Qt dialog runs."""
        if self.dialog_closed:
            return
        try:
            PyCadInputQueue.PythonMainLoop()
        except Exception as ex:
            _write_log("MICROSTATION PUMP | PythonMainLoop exception | " + str(ex))

    def toggle_source_pick(self):
        """Starts or cancels native source selection."""
        if self.source_pick_active:
            self.cancel_source_pick()
        else:
            self.begin_source_pick()

    def _hide_for_pick(self):
        """Preserves the dialog position while MicroStation receives picks."""
        self._saved_position = self.pos()
        self.hide()

    def _restore_after_pick(self):
        """Shows the dialog where the user last placed it."""
        if self.dialog_closed:
            return
        if self._saved_position is not None:
            self.move(self._saved_position)
        self.show()
        self.raise_()
        self.activateWindow()

    def begin_source_pick(self):
        """Starts MicroStation's normal single-element selection command."""
        if self.source_pick_active or self.target_pick_active:
            return
        try:
            SelectionSetManager.GetManager().EmptyAll()
        except Exception:
            pass
        self.source_pick_active = True
        self.source_button.setText("Cancel Source Pick")
        self.assign_button.setEnabled(False)
        self.status_label.setText(
            "Source pick active: select exactly ONE element in MicroStation."
        )
        _write_log("SOURCE PICK | begin | cooperative MicroStation pump active")
        try:
            start_native_single_element_selection()
        except Exception as ex:
            self.source_pick_active = False
            self.source_button.setText("Select Source Element")
            self.status_label.setText(
                "Could not start MicroStation Element Selection: " + _short_error(ex)
            )
            _write_log("SOURCE PICK | native selector failed | " + str(ex))
            self._update_item_type_selection(update_status=False)
            return
        self._hide_for_pick()
        _prompt(
            "Item Type Painter: Select ONE SOURCE element. "
            "MicroStation Element Selection is active."
        )
        self._source_timer.start()

    def _poll_source_selection(self):
        """Reads the ordinary SelectionSet until one source is captured."""
        if not self.source_pick_active:
            self._source_timer.stop()
            return
        try:
            sel_mgr = SelectionSetManager.GetManager()
            count = int(sel_mgr.NumSelected())
            if count != self._last_source_selection_count:
                _write_log(f"SOURCE PICK | SelectionSet count={count}")
                self._last_source_selection_count = count
        except Exception as ex:
            self.cancel_source_pick(restore_status=False)
            self.status_label.setText(
                "Could not read MicroStation's SelectionSet: " + str(ex)
            )
            return
        if count <= 0:
            return
        if count != 1:
            try:
                sel_mgr.EmptyAll()
                start_native_single_element_selection()
            except Exception:
                pass
            self._last_source_selection_count = 0
            self.status_label.setText(
                f"{count} elements were selected. Select exactly ONE source element."
            )
            _prompt(
                "Item Type Painter: Multiple source elements were selected. "
                "Selection cleared; pick exactly ONE source element."
            )
            return
        try:
            snapshot = get_source_snapshot_from_selection()
        except Exception as ex:
            try:
                sel_mgr.EmptyAll()
                start_native_single_element_selection()
            except Exception:
                pass
            self._last_source_selection_count = 0
            self.status_label.setText(
                "Could not interrogate the selected source: " + _short_error(ex)
            )
            _prompt("Item Type Painter: Source interrogation failed - " + _short_error(ex))
            return
        self.source_snapshot = snapshot
        self.source_pick_active = False
        self._source_timer.stop()
        self.source_button.setText("Select Source Element")
        try:
            sel_mgr.EmptyAll()
        except Exception:
            pass
        return_to_default_command()
        self._restore_after_pick()
        _write_log(
            f"SOURCE CAPTURE | element={snapshot.get('source_element_id', 'Unknown')} | "
            f"item_types={len(snapshot.get('items', []))}"
        )
        _prompt(
            f"Item Type Painter: Source element "
            f"{snapshot.get('source_element_id', 'Unknown')} captured."
        )
        self.refresh_source_display()

    def cancel_source_pick(self, restore_status=True):
        """Cancels source selection and returns to the review dialog."""
        self._source_timer.stop()
        self.source_pick_active = False
        try:
            SelectionSetManager.GetManager().EmptyAll()
        except Exception:
            pass
        return_to_default_command()
        self._restore_after_pick()
        self.source_button.setText("Select Source Element")
        self._update_item_type_selection(update_status=False)
        if restore_status:
            if self.source_snapshot is not None:
                self._update_item_type_selection()
            else:
                self.status_label.setText(
                    "Source picking canceled. Click 'Select Source Element' to try again."
                )
        _prompt("Item Type Painter: Source picking canceled.")

    def assign_targets(self):
        """Starts one target run without closing the review dialog."""
        if self.dialog_closed or self.source_pick_active or self.target_pick_active:
            return
        selected_snapshot = self._selected_snapshot()
        if not source_snapshot_is_assignable(selected_snapshot):
            self._update_item_type_selection()
            return
        self.target_pick_active = True
        self.assign_button.setEnabled(False)
        self.source_button.setEnabled(False)
        self.status_label.setText(
            "Select target elements in MicroStation; right-click to accept."
        )
        try:
            self._hide_for_pick()
            clear_picker_highlights(None)
            controller = TargetAssignmentController(selected_snapshot, self)
            TargetAssignmentController.s_instance = controller
            ItemTypeTargetPickTool.InstallNewInstance(
                TARGET_PICK_TOOL_ID,
                selected_snapshot["source_element_id"],
                controller.on_targets_complete,
                controller.on_abort,
            )
        except Exception as ex:
            TargetAssignmentController.s_instance = None
            clear_picker_highlights(None)
            return_to_default_command()
            self.on_target_pick_finished(
                "Could not start target selection: " + _short_error(ex)
            )
            _msg_error(SCRIPT_TITLE, "Could not start target selection:\n" + str(ex))

    def on_target_pick_finished(self, status):
        """Restores source and target controls after one target run."""
        if self.dialog_closed:
            return
        self.target_pick_active = False
        self.source_button.setEnabled(True)
        self._update_item_type_selection(update_status=False)
        self.status_label.setText(status)
        self._restore_after_pick()

    def reject(self):
        """Uses Escape to cancel source picking or close the dialog."""
        if self.source_pick_active:
            self.cancel_source_pick()
        else:
            self.close()

    def closeEvent(self, event):
        """Closes the dialog only when the native target picker is idle."""
        if self.target_pick_active:
            self.status_label.setText(
                "Finish or cancel target selection in MicroStation before closing."
            )
            event.ignore()
            return
        if self.source_pick_active:
            self.cancel_source_pick(restore_status=False)
        self.dialog_closed = True
        self._source_timer.stop()
        self._pump_timer.stop()
        event.accept()
        if self._event_loop is not None:
            self._event_loop.quit()

    def run(self):
        """Runs a local Qt event loop until the user closes the dialog."""
        self._event_loop = QtCore.QEventLoop(self)
        self._pump_timer.start()
        self.show()
        self._event_loop.exec_()


# ================================================================
# POST-PICK ASSIGNMENT CONTROLLER
# ================================================================

class TargetAssignmentController:

    s_instance = None

    def __init__(
        self,
        source_snapshot,
        dialog,
    ):
        self.source_snapshot = source_snapshot
        self.dialog = dialog
        self.finished = False
        self.restore_queued = False

    def _restore_dialog(self, status):
        """Queues dialog restoration after the native cleanup callback returns."""
        if self.restore_queued:
            return
        self.restore_queued = True
        TargetAssignmentController.s_instance = None
        if not self.dialog.dialog_closed:
            QtCore.QTimer.singleShot(0, lambda: self.dialog.on_target_pick_finished(status))

    def on_callback_failure(self, error):
        """Restores the dialog if a post-cleanup step raises unexpectedly."""
        _write_log("TARGET CALLBACK | unexpected error | " + str(error))
        self._restore_dialog("Target assignment stopped. Review the MicroStation message and try again.")


    def on_targets_complete(
        self,
        target_ids,
    ):
        """
        Called only after ItemTypeTargetPickTool._OnCleanup() has cleared the
        agenda, called Bentley base cleanup, cleared the SelectionSet, and
        returned MicroStation to its default command.
        """
        if self.finished:
            return

        self.finished = True

        if not target_ids:

            text = (
                "Item Type Painter: No target elements were accepted. "
                "No Item Types were changed."
            )

            _prompt(
                text
            )

            self._restore_dialog("No target elements were accepted. Select targets to try again.")

            return

        _prompt(
            f"Item Type Painter: Applying source metadata to "
            f"{len(target_ids)} accepted target(s)..."
        )

        try:

            summary = apply_snapshot_to_target_ids(
                self.source_snapshot,
                target_ids,
            )

        except Exception as ex:

            _msg_error(
                SCRIPT_TITLE,
                "Target assignment failed after picker cleanup:\n"
                +
                str(ex),
            )

            self._restore_dialog("Target assignment failed. Review the MicroStation message and try again.")

            return

        # --------------------------------------------------------
        # FINAL TARGET SELECTION RESET
        #
        # Deliberately select every retained target in MicroStation's real
        # SelectionSet, materialize the full set with BuildAgenda(), then
        # immediately de-select it. This is the proven ShoulderHatch cleanup
        # pattern requested for the Item Type Painter.
        # --------------------------------------------------------

        selection_reset_count = (
            force_select_then_deselect_elements(
                summary.get(
                    "target_element_ids",
                    [],
                )
            )
        )

        summary[
            "selection_reset_count"
        ] = selection_reset_count

        item_type_count = int(
            summary.get(
                "source_item_type_count",
                0,
            )
        )

        item_type_applied_elements = int(
            summary.get(
                "item_types_applied_element_count",
                0,
            )
        )

        text = (
            f"Item Type Painter complete: "
            f"{item_type_count} Item Type(s) applied to "
            f"{item_type_applied_elements} element(s). "
            f"Property updates: {summary['assigned_count']} complete, "
            f"{summary['partial_count']} partial, "
            f"{summary['failed_count']} failed. "
            f"Selection reset: {selection_reset_count} element(s). "
            f"Write log: {summary.get('log_path', WRITE_LOG_PATH)}"
        )

        _prompt(
            text
        )

        try:
            MessageCenter.ShowInfoMessage(
                "Item Type Painter",
                text,
                False,
            )
        except Exception:
            print(text)

        # User-requested modal completion notification.
        show_completion_dialog(
            item_type_count,
            item_type_applied_elements,
            summary.get(
                "partial_count",
                0,
            ),
            summary.get(
                "failed_count",
                0,
            ),
        )

        self._restore_dialog(
            f"Applied {item_type_count} Item Type(s) to {item_type_applied_elements} element(s). "
            "Select more targets or re-pick the source."
        )


    def on_abort(
        self,
    ):

        if self.finished:
            return

        self.finished = True

        clear_picker_highlights(
            None
        )

        return_to_default_command()

        _prompt(
            "Item Type Painter target selection canceled."
        )

        self._restore_dialog("Target selection canceled. Select targets to try again.")


# ================================================================
# MAIN
# ================================================================

def main():

    _reset_write_log()
    _write_log("SCRIPT START | cooperative Qt/MicroStation pump")

    try:
        get_active_context()

    except Exception as ex:

        _msg_error(
            SCRIPT_TITLE,
            ex,
        )

        return

    # ------------------------------------------------------------
    # OPTIONAL INITIAL SOURCE
    #
    # A preselected single element is still accepted as a convenience, but
    # v0.18 no longer REQUIRES preselection. The UI source-pick button is the
    # normal production workflow.
    # ------------------------------------------------------------

    source_snapshot = None

    try:

        sel_mgr = SelectionSetManager.GetManager()

        if int(
            sel_mgr.NumSelected()
        ) == 1:

            source_snapshot = (
                get_source_snapshot_from_selection()
            )

    except Exception as ex:

        _write_log(
            "INITIAL SOURCE READ | ignored | "
            +
            str(ex)
        )

        source_snapshot = None

    # Keep one nonmodal Qt dialog alive for repeated source and target runs.
    # The native target picker still cleans up before its callback writes EC data.
    dialog = ItemTypePainterDialog(source_snapshot)
    dialog.run()
    clear_picker_highlights(None)
    return_to_default_command()
    _prompt("Item Type Painter closed.")


if __name__ == "__main__":

    main()
