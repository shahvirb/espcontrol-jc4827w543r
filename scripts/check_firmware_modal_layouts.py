#!/usr/bin/env python3
"""Compile and exercise the pure firmware modal layout planner."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from device_profiles import ROOT, load_device_profiles


FIXTURES = ROOT / "common" / "config" / "modal_layout_geometry_fixtures.json"
HEADER = ROOT / "components" / "espcontrol" / "button_grid_modal_layout.h"

FAMILY_ENUMS = {
    "compact-square": "COMPACT_SQUARE",
    "large-square": "LARGE_SQUARE",
    "compact-portrait": "COMPACT_PORTRAIT",
    "wide-landscape": "WIDE_LANDSCAPE",
    "large-landscape": "LARGE_LANDSCAPE",
}
DENSITY_ENUMS = {
    "compact": "COMPACT",
    "comfortable": "COMFORTABLE",
    "spacious": "SPACIOUS",
}
MEMORY_ENUMS = {
    "standard": "STANDARD",
    "constrained": "CONSTRAINED",
}


def parse_resolution(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"([1-9]\d*)\s*x\s*([1-9]\d*)", value.strip())
    if not match:
        raise AssertionError(f"invalid public resolution: {value!r}")
    return int(match.group(1)), int(match.group(2))


def assert_profile_contract(fixtures: dict, profiles: dict[str, dict]) -> None:
    fixture_by_slug = {entry["slug"]: entry for entry in fixtures["layouts"]}
    missing = sorted(set(profiles) - set(fixture_by_slug))
    allowed_aliases = {
        "guition-esp32-p4-jc4880p443-v3": "guition-esp32-p4-jc4880p443",
        "guition-esp32-p4-jc8012p4a1-v2": "guition-esp32-p4-jc8012p4a1",
        "guition-esp32-p4-jc8012p4a1-v3": "guition-esp32-p4-jc8012p4a1",
        "guition-esp32-p4-jc1060p470-v2": "guition-esp32-p4-jc1060p470",
    }
    unexpected = sorted(set(missing) - set(allowed_aliases))
    assert not unexpected, f"modal geometry fixtures missing devices: {', '.join(unexpected)}"

    for slug, profile in profiles.items():
        fixture_slug = allowed_aliases.get(slug, slug)
        fixture = fixture_by_slug[fixture_slug]
        modal = profile["firmware"]["display"]["modal"]
        expected_profile = fixture["profile"]
        assert modal["layoutFamily"] == expected_profile["family"], f"{slug}: modal family drifted"
        assert modal["density"] == expected_profile["density"], f"{slug}: modal density drifted"
        assert modal["memoryTier"] == expected_profile["memoryTier"], f"{slug}: modal memory tier drifted"
        assert modal["baseTouchTarget"] == expected_profile["baseTouchTarget"], (
            f"{slug}: modal base touch target drifted"
        )
        assert parse_resolution(profile["public"]["resolution"]) == (
            fixture["viewport"]["width"], fixture["viewport"]["height"]
        ), f"{slug}: fixture viewport does not match public resolution"

        coverage = fixture.get("coverage")
        if coverage is not None:
            rotation = profile.get("rotation", {})
            assert rotation.get("enabled"), f"{slug}: coverage requires rotation support"
            assert coverage["rotations"] == rotation.get("options"), (
                f"{slug}: fixture rotations do not match the profile"
            )


def check_fixture_schema(fixtures: dict) -> None:
    """Reject incomplete snapshots before generating a less useful C++ error."""
    assert isinstance(fixtures.get("layouts"), list), "modal layout fixtures must contain layouts"
    slugs = [entry.get("slug") for entry in fixtures["layouts"]]
    assert len(slugs) == len(set(slugs)), "modal layout fixtures contain duplicate slugs"
    required = {"slug", "profile", "viewport", "panelInsets", "expected"}

    def check_snapshot_shape(slug: str, name: str, snapshot: dict) -> None:
        required_snapshot = {
            "panel", "back", "arcSize", "controlsCenterY", "tabs", "content", "speakerContent",
            "fallbackHeight",
        }
        missing_snapshot = sorted(required_snapshot - set(snapshot))
        assert not missing_snapshot, (
            f"{slug}: {name} missing keys: {', '.join(missing_snapshot)}"
        )
        for section in ("panel", "back", "tabs", "content", "speakerContent"):
            assert isinstance(snapshot[section], dict), f"{slug}: {name}.{section} must be an object"

    for entry in fixtures["layouts"]:
        missing = sorted(required - set(entry))
        assert not missing, f"{entry.get('slug', '<unknown>')}: missing fixture keys: {', '.join(missing)}"
        if "coverage" not in entry:
            continue
        coverage = entry["coverage"]
        for key in (
            "rotations",
            "mediaTabCounts",
            "climateTabCounts",
            "standaloneTabCount",
            "scrollableMinimumHeight",
            "enforceTabTouchTarget",
        ):
            assert key in coverage, f"{entry['slug']}: coverage missing {key}"
        assert entry.get("compactPanelInsets"), (
            f"{entry['slug']}: rotation coverage requires compactPanelInsets"
        )
        assert coverage["mediaTabCounts"] == list(range(1, 6)), (
            f"{entry['slug']}: media coverage must exercise counts 1..5"
        )
        assert coverage["climateTabCounts"] == list(range(1, 7)), (
            f"{entry['slug']}: climate coverage must exercise counts 1..6"
        )
        assert coverage["standaloneTabCount"] == 0, (
            f"{entry['slug']}: standalone coverage must exercise count 0"
        )
        assert "compactSnapshot" in entry, f"{entry['slug']}: coverage requires compactSnapshot"
        assert "rotatedSnapshot" in entry, f"{entry['slug']}: coverage requires rotatedSnapshot"
        check_snapshot_shape(entry["slug"], "compactSnapshot", entry["compactSnapshot"])
        rotated = entry["rotatedSnapshot"]
        assert set(rotated) == {"normal", "compact"}, (
            f"{entry['slug']}: rotatedSnapshot must contain normal and compact"
        )
        check_snapshot_shape(entry["slug"], "rotatedSnapshot.normal", rotated["normal"])
        check_snapshot_shape(entry["slug"], "rotatedSnapshot.compact", rotated["compact"])

    jc = next((entry for entry in fixtures["layouts"] if entry.get("slug") == "guition-jc4827w543r"), None)
    assert jc is not None, "JC4827 modal fixture is required"
    assert "coverage" in jc, "JC4827 modal fixture coverage is required"
    # Source contract: common/config/display.yaml supplies normal top padding
    # 30 and compact top padding 4; both modes use left/right 5 and bottom 4.
    # components/espcontrol/button_grid_media.h supplies the speaker row's
    # actual 76px minimum. These are not tunable fixture defaults: relaxing
    # them would disable the JC regression checks.
    assert jc["panelInsets"] == {"left": 5, "top": 30, "right": 5, "bottom": 4}, (
        "JC4827 normal panel insets must remain source-evidenced 5/30/5/4"
    )
    assert jc["compactPanelInsets"] == {"left": 5, "top": 4, "right": 5, "bottom": 4}, (
        "JC4827 compact panel insets must remain source-evidenced 5/4/5/4"
    )
    assert jc["coverage"]["scrollableMinimumHeight"] == 76, (
        "JC4827 scrollable row minimum must remain source-evidenced 76px"
    )
    assert jc["coverage"]["enforceTabTouchTarget"] is True, (
        "JC4827 tab touch-target enforcement cannot be disabled"
    )


def snapshot_initializer(snapshot: dict) -> str:
    panel = snapshot["panel"]
    back = snapshot["back"]
    tabs = snapshot["tabs"]
    content = snapshot["content"]
    speaker = snapshot["speakerContent"]
    arc_size = snapshot["arcSize"] if "arcSize" in snapshot else snapshot["arc"]["size"]
    controls_center_y = snapshot["controlsCenterY"]
    values = (
        panel["x"], panel["y"], panel["width"], panel["height"],
        back["size"], back["x"], back["y"],
        arc_size, controls_center_y,
        snapshot["fallbackHeight"],
        tabs["size"], tabs["selectedSize"], tabs["gap"], tabs["frameWidth"],
        tabs["frameHeight"], tabs["safeLeft"], tabs["rowLeft"], tabs["contentGap"],
        content["top"], content["bottom"], content["width"], content["height"], content["centerY"],
        speaker["top"], speaker["bottom"], speaker["width"], speaker["height"], speaker["centerY"],
    )
    return ", ".join(str(value) for value in values)


def cpp_assertions(entry: dict, index: int) -> list[str]:
    profile = entry["profile"]
    viewport = entry["viewport"]
    insets = entry["panelInsets"]
    expected = entry["expected"]
    panel = expected["panel"]
    back = expected["back"]
    arc = expected["arc"]
    tabs = expected["tabs"]
    content = expected["content"]
    prefix = f"layout_{index}"
    label = entry["slug"]
    scroll_minimum_height = entry.get("coverage", {}).get("scrollableMinimumHeight", 0)
    enforce_tab_touch_target = entry.get("coverage", {}).get("enforceTabTouchTarget", False)
    tab_touch_target = profile["baseTouchTarget"] if enforce_tab_touch_target else 0
    # The snapshot records the planner's scaled, actual hitbox.  Usability is
    # deliberately checked separately below because a truthful JC snapshot is
    # 26 px while its profile target remains 46 px.
    lines = [
        "  {",
        "    DeviceProfile profile;",
        f"    profile.layout_family = LayoutFamily::{FAMILY_ENUMS[profile['family']]};",
        f"    profile.density = Density::{DENSITY_ENUMS[profile['density']]};",
        f"    profile.memory_tier = MemoryTier::{MEMORY_ENUMS[profile['memoryTier']]};",
        f"    profile.base_touch_target = {profile['baseTouchTarget']};",
        "    FrameRequest request;",
        f"    request.screen_width = {viewport['width']};",
        f"    request.screen_height = {viewport['height']};",
        f"    request.panel_left = {insets['left']};",
        f"    request.panel_top = {insets['top']};",
        f"    request.panel_right = {insets['right']};",
        f"    request.panel_bottom = {insets['bottom']};",
        "    const FrameLayout layout = calculate_frame(profile, request);",
        f'    snapshot_check(layout.panel_x == {panel["x"]}, "{label}: panel x");',
        f'    snapshot_check(layout.panel_y == {panel["y"]}, "{label}: panel y");',
        f'    snapshot_check(layout.panel_width == {panel["width"]}, "{label}: panel width");',
        f'    snapshot_check(layout.panel_height == {panel["height"]}, "{label}: panel height");',
        f'    snapshot_check(layout.short_side == {expected["shortSide"]}, "{label}: short side");',
        f'    snapshot_check(layout.inset == {expected["inset"]}, "{label}: inset");',
        f'    snapshot_check(layout.back_size == {back["size"]}, "{label}: back size");',
        f'    snapshot_check(layout.back_inset_x == {back["x"]}, "{label}: back x");',
        f'    snapshot_check(layout.back_inset_y == {back["y"]}, "{label}: back y");',
        f'    snapshot_check(layout.button_size == {expected["buttonSize"]}, "{label}: button size");',
        f'    snapshot_check(layout.arc_size == {arc["size"]}, "{label}: arc size");',
        f'    snapshot_check(layout.arc_stroke == {arc["stroke"]}, "{label}: arc stroke");',
        f'    snapshot_check(layout.arc_center_x == {arc["centerX"]}, "{label}: arc center x");',
        f'    snapshot_check(layout.controls_center_y == {expected["controlsCenterY"]}, "{label}: controls center");',
        "    usability_check(layout.back_size >= profile.base_touch_target,",
        f'                    "{label}: back target");',
        "    usability_check(layout.panel_width > layout.inset * 2,",
        f'                    "{label}: panel width");',
        "    usability_check(layout.panel_height > layout.inset * 2,",
        f'                    "{label}: panel height");',
        "    TabRequest tab_request;",
        "    tab_request.tab_count = 5;",
        "    tab_request.show_tab_bar = true;",
        "    const TabLayout tabs = calculate_tabs(profile, layout, tab_request);",
        f'    snapshot_check(tabs.tab_size == {tabs["size"]}, "{label}: five tabs size");',
        f'    snapshot_check(tabs.selected_tab_size == {tabs["selectedSize"]}, "{label}: five tabs selected size");',
        f'    snapshot_check(tabs.tab_gap == {tabs["gap"]}, "{label}: five tabs gap");',
        f'    snapshot_check(tabs.frame_width == {tabs["frameWidth"]}, "{label}: five tabs frame width");',
        f'    snapshot_check(tabs.frame_height == {tabs["frameHeight"]}, "{label}: five tabs frame height");',
        f'    snapshot_check(tabs.safe_left == {tabs["safeLeft"]}, "{label}: five tabs safe left");',
        f'    snapshot_check(tabs.row_left == {tabs["rowLeft"]}, "{label}: five tabs row left");',
        f'    snapshot_check(tabs.content_gap == {tabs["contentGap"]}, "{label}: five tabs content gap");',
        f'    snapshot_check(tab_icon_zoom(profile) == {tabs["iconZoom"]}, "{label}: tab icon zoom");',
        f'    check_tabs(tabs, layout, 5, true, {tab_touch_target}, "{label}: five tabs");',
        "    ContentRequest content_request;",
        "    content_request.show_tab_bar = true;",
        "    content_request.tab_frame_height = tabs.frame_height;",
        "    content_request.tab_content_gap = tabs.content_gap;",
        "    content_request.minimum_height = 160;",
        "    const ContentLayout content = calculate_content(layout, content_request);",
        f'    snapshot_check(content.top == {content["top"]}, "{label}: content top");',
        f'    snapshot_check(content.bottom == {content["bottom"]}, "{label}: content bottom");',
        f'    snapshot_check(content.width == {content["width"]}, "{label}: content width");',
        f'    snapshot_check(content.height == {content["height"]}, "{label}: content height");',
        f'    snapshot_check(content.center_y == {content["centerY"]}, "{label}: content center");',
        f'    check_content(layout, content, 160, 0, "{label}: content");',
        "    TabRequest climate_tabs_request;",
        "    climate_tabs_request.tab_count = 6;",
        "    climate_tabs_request.show_tab_bar = true;",
        "    const TabLayout climate_tabs = calculate_tabs(profile, layout, climate_tabs_request);",
        f'    check_tabs(climate_tabs, layout, 6, true, {tab_touch_target}, "{label}: six climate tabs");',
        "    TabRequest speaker_tabs_request;",
        "    speaker_tabs_request.tab_count = 4;",
        "    speaker_tabs_request.show_tab_bar = true;",
        "    const TabLayout speaker_tabs = calculate_tabs(profile, layout, speaker_tabs_request);",
        f'    check_tabs(speaker_tabs, layout, 4, true, {tab_touch_target}, "{label}: four media tabs");',
        "    ContentRequest speaker_content_request;",
        "    speaker_content_request.show_tab_bar = true;",
        "    speaker_content_request.tab_frame_height = speaker_tabs.frame_height;",
        "    speaker_content_request.tab_content_gap = speaker_tabs.content_gap;",
        "    speaker_content_request.minimum_height = 180;",
        "    speaker_content_request.fallback_height = layout.panel_height / 2;",
        "    const ContentLayout speaker_content = calculate_content(layout, speaker_content_request);",
        f'    check_content(layout, speaker_content, 180, {scroll_minimum_height}, "{label}: speaker content");',
        "    TabRequest standalone_tabs_request;",
        "    standalone_tabs_request.tab_count = 0;",
        "    standalone_tabs_request.show_tab_bar = false;",
        "    const TabLayout standalone_tabs = calculate_tabs(profile, layout, standalone_tabs_request);",
        f'    check_tabs(standalone_tabs, layout, 1, false, {tab_touch_target}, "{label}: standalone tabs");',
        "    ContentRequest standalone_content_request;",
        "    standalone_content_request.show_tab_bar = false;",
        "    standalone_content_request.top_without_tabs = layout.inset * 2;",
        "    standalone_content_request.safe_top = layout.back_inset_y + layout.back_size + scaled_px(12, layout.short_side);",
        "    standalone_content_request.minimum_height = 180;",
        "    standalone_content_request.fallback_height = layout.panel_height / 2;",
        "    const ContentLayout standalone_content = calculate_content(layout, standalone_content_request);",
        f'    usability_check(standalone_content.top == standalone_content_request.safe_top, "{label}: standalone safe top");',
        f'    check_content(layout, standalone_content, 180, {scroll_minimum_height}, "{label}: standalone content");',
    ]

    coverage = entry.get("coverage")
    if coverage:
        media_name = f"{prefix}_media_counts"
        climate_name = f"{prefix}_climate_counts"
        media_counts = ", ".join(str(value) for value in coverage["mediaTabCounts"])
        climate_counts = ", ".join(str(value) for value in coverage["climateTabCounts"])
        rotations = ", ".join(coverage["rotations"])
        expected_snapshots = {
            "normal": entry["expected"],
            "compact": entry["compactSnapshot"],
            "rotatedNormal": entry["rotatedSnapshot"]["normal"],
            "rotatedCompact": entry["rotatedSnapshot"]["compact"],
        }
        lines.extend([
            f"    const int {media_name}[] = {{{media_counts}}};",
            f"    const int {climate_name}[] = {{{climate_counts}}};",
        ])
        for mode, mode_insets, mode_label, snapshot_name, rotated_snapshot_name in (
            ("normal", entry["panelInsets"], "normal", "normal", "rotatedNormal"),
            ("compact", entry["compactPanelInsets"], "compact", "compact", "rotatedCompact"),
        ):
            normal_snapshot = snapshot_initializer(expected_snapshots[snapshot_name])
            rotated_snapshot = snapshot_initializer(expected_snapshots[rotated_snapshot_name])
            normal_var = f"{prefix}_{mode}_snapshot"
            rotated_var = f"{prefix}_{mode}_rotated_snapshot"
            request_var = f"{prefix}_{mode}_request"
            lines.extend([
                f"    const LayoutSnapshot {normal_var} = {{{normal_snapshot}}};",
                f"    const LayoutSnapshot {rotated_var} = {{{rotated_snapshot}}};",
                f"    FrameRequest {request_var} = request;",
                f"    {request_var}.panel_left = {mode_insets['left']};",
                f"    {request_var}.panel_top = {mode_insets['top']};",
                f"    {request_var}.panel_right = {mode_insets['right']};",
                f"    {request_var}.panel_bottom = {mode_insets['bottom']};",
                f"    for (int rotation : {{{rotations}}}) {{",
                f"      FrameRequest rotated_request = {request_var};",
                "      if (rotation == 90 || rotation == 270) {",
                "        const int original_width = rotated_request.screen_width;",
                "        rotated_request.screen_width = rotated_request.screen_height;",
                "        rotated_request.screen_height = original_width;",
                "      }",
                f'      check_coverage(profile, rotated_request, "{label} {mode_label}", rotation,',
                f"                     {media_name}, {len(coverage['mediaTabCounts'])},",
                f"                     {climate_name}, {len(coverage['climateTabCounts'])},",
                f"                     {coverage['standaloneTabCount']}, {coverage['scrollableMinimumHeight']}, {tab_touch_target},",
                f"                     {normal_var}, {rotated_var});",
                "    }",
            ])

    lines.extend([f'    (void) "{prefix}";', "  }"])
    return lines


def compile_layout_contract(fixtures: dict) -> int:
    compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
    if compiler is None:
        raise RuntimeError("a C++ compiler is required for firmware modal layout checks")

    source = [
        "#include <iostream>",
        "#include <string>",
        f'#include "{HEADER}"',
        "using namespace espcontrol::modal;",
        "int snapshot_checks = 0;",
        "int snapshot_failures = 0;",
        "int usability_checks = 0;",
        "int usability_failures = 0;",
        "void snapshot_check(bool okay, const std::string &label) {",
        "  ++snapshot_checks;",
        "  if (!okay) { ++snapshot_failures; std::cout << \"SNAPSHOT FAIL: \" << label << '\\n'; }",
        "}",
        "void usability_check(bool okay, const std::string &label) {",
        "  ++usability_checks;",
        "  if (!okay) { ++usability_failures; std::cout << \"USABILITY FAIL: \" << label << '\\n'; }",
        "}",
        "void check_tabs(const TabLayout &tabs, const FrameLayout &frame, int expected_count,",
        "                bool expected_show, int tab_touch_target,",
        "                const std::string &label) {",
        "  usability_check(tabs.tab_count == expected_count, label + \" normalized tab count\");",
        "  usability_check(tabs.show_tab_bar == expected_show, label + \" show bar\");",
        "  if (expected_show) {",
        "    usability_check(tabs.tab_size > 0, label + \" positive tab size\");",
        "    usability_check(tabs.row_left >= 0, label + \" row starts in panel\");",
        "    usability_check(tabs.row_left >= tabs.safe_left, label + \" row clears Back\");",
        "    usability_check(tabs.row_left + tabs.frame_width <= frame.panel_width,",
        "                    label + \" row fits panel\");",
        "    if (tab_touch_target > 0) {",
        "      // Only profiles that opt into this contract promise tab-sized targets.",
        "      usability_check(tabs.tab_size >= tab_touch_target, label + \" tab touch target\");",
        "    }",
        "  } else {",
        "    usability_check(tabs.frame_height == 0, label + \" hidden row has no height\");",
        "  }",
        "}",
        "struct LayoutSnapshot {",
        "  int panel_x, panel_y, panel_width, panel_height;",
        "  int back_size, back_inset_x, back_inset_y;",
        "  int arc_size, controls_center_y;",
        "  int fallback_height;",
        "  int tab_size, selected_tab_size, tab_gap, frame_width, frame_height;",
        "  int safe_left, row_left, content_gap;",
        "  int content_top, content_bottom, content_width, content_height, content_center_y;",
        "  int speaker_top, speaker_bottom, speaker_width, speaker_height, speaker_center_y;",
        "};",
        "void check_layout_snapshot(const FrameLayout &frame, const TabLayout &tabs,",
        "                           const ContentLayout &content, const ContentLayout &speaker,",
        "                           int speaker_fallback_height,",
        "                           const LayoutSnapshot &expected, const std::string &label) {",
        "  snapshot_check(frame.panel_x == expected.panel_x, label + \" panel x\");",
        "  snapshot_check(frame.panel_y == expected.panel_y, label + \" panel y\");",
        "  snapshot_check(frame.panel_width == expected.panel_width, label + \" panel width\");",
        "  snapshot_check(frame.panel_height == expected.panel_height, label + \" panel height\");",
        "  snapshot_check(frame.back_size == expected.back_size, label + \" back size\");",
        "  snapshot_check(frame.back_inset_x == expected.back_inset_x, label + \" back x\");",
        "  snapshot_check(frame.back_inset_y == expected.back_inset_y, label + \" back y\");",
        "  snapshot_check(frame.arc_size == expected.arc_size, label + \" arc size\");",
        "  snapshot_check(frame.controls_center_y == expected.controls_center_y, label + \" controls center\");",
        "  snapshot_check(speaker_fallback_height == expected.fallback_height, label + \" fallback height\");",
        "  snapshot_check(tabs.tab_size == expected.tab_size, label + \" tab size\");",
        "  snapshot_check(tabs.selected_tab_size == expected.selected_tab_size, label + \" selected tab size\");",
        "  snapshot_check(tabs.tab_gap == expected.tab_gap, label + \" tab gap\");",
        "  snapshot_check(tabs.frame_width == expected.frame_width, label + \" tab frame width\");",
        "  snapshot_check(tabs.frame_height == expected.frame_height, label + \" tab frame height\");",
        "  snapshot_check(tabs.safe_left == expected.safe_left, label + \" tab safe left\");",
        "  snapshot_check(tabs.row_left == expected.row_left, label + \" tab row left\");",
        "  snapshot_check(tabs.content_gap == expected.content_gap, label + \" tab content gap\");",
        "  snapshot_check(content.top == expected.content_top, label + \" content top\");",
        "  snapshot_check(content.bottom == expected.content_bottom, label + \" content bottom\");",
        "  snapshot_check(content.width == expected.content_width, label + \" content width\");",
        "  snapshot_check(content.height == expected.content_height, label + \" content height\");",
        "  snapshot_check(content.center_y == expected.content_center_y, label + \" content center\");",
        "  snapshot_check(speaker.top == expected.speaker_top, label + \" speaker top\");",
        "  snapshot_check(speaker.bottom == expected.speaker_bottom, label + \" speaker bottom\");",
        "  snapshot_check(speaker.width == expected.speaker_width, label + \" speaker width\");",
        "  snapshot_check(speaker.height == expected.speaker_height, label + \" speaker height\");",
        "  snapshot_check(speaker.center_y == expected.speaker_center_y, label + \" speaker center\");",
        "}",
        "void check_content(const FrameLayout &frame, const ContentLayout &content,",
        "                   int minimum_height, int scrollable_minimum_height,",
        "                   const std::string &label) {",
        "  usability_check(content.top >= frame.inset, label + \" top is inset\");",
        "  usability_check(content.bottom <= frame.panel_height, label + \" bottom is panel bound\");",
        "  usability_check(content.width > 0 && content.width <= frame.panel_width,",
        "                  label + \" width is positive and fitting\");",
        "  usability_check(content.height > 0, label + \" height is positive\");",
        "  usability_check(content.top + content.height <= content.bottom,",
        "                  label + \" content rectangle fits\");",
        "  const int natural_height = content.bottom - content.top;",
        "  const int expected_height = natural_height < minimum_height",
        "    ? frame.panel_height / 2 : natural_height;",
        "  usability_check(content.height == expected_height, label + \" production fallback\");",
        "  if (scrollable_minimum_height > 0) {",
        "    // This is the production scrollable-content row minimum (76 on JC),",
        "    // not proof that every LVGL row fits or remains accessible.",
        "    usability_check(content.height >= scrollable_minimum_height,",
        "                    label + \" scrollable row minimum\");",
        "  }",
        "}",
        "void check_coverage(const DeviceProfile &profile, const FrameRequest &request,",
        "                    const char *label, int rotation,",
        "                    const int *media_counts, int media_count,",
        "                    const int *climate_counts, int climate_count,",
        "                    int standalone_tab_count, int scrollable_minimum_height,",
        "                    int tab_touch_target,",
        "                    const LayoutSnapshot &landscape_snapshot,",
        "                    const LayoutSnapshot &portrait_snapshot) {",
        "  const FrameLayout frame = calculate_frame(profile, request);",
        "  const std::string rotation_label = std::string(label) + \" rotation \" + std::to_string(rotation);",
        "  usability_check(frame.back_size >= profile.base_touch_target, rotation_label + \" back target\");",
        "  TabRequest snapshot_tab_request;",
        "  snapshot_tab_request.tab_count = 5;",
        "  snapshot_tab_request.show_tab_bar = true;",
        "  const TabLayout snapshot_tabs = calculate_tabs(profile, frame, snapshot_tab_request);",
        "  ContentRequest snapshot_content_request;",
        "  snapshot_content_request.show_tab_bar = true;",
        "  snapshot_content_request.tab_frame_height = snapshot_tabs.frame_height;",
        "  snapshot_content_request.tab_content_gap = snapshot_tabs.content_gap;",
        "  snapshot_content_request.minimum_height = 160;",
        "  const ContentLayout snapshot_content = calculate_content(frame, snapshot_content_request);",
        "  ContentRequest snapshot_speaker_request;",
        "  snapshot_speaker_request.show_tab_bar = true;",
        "  snapshot_speaker_request.tab_frame_height = snapshot_tabs.frame_height;",
        "  snapshot_speaker_request.tab_content_gap = snapshot_tabs.content_gap;",
        "  snapshot_speaker_request.minimum_height = 180;",
        "  snapshot_speaker_request.fallback_height = frame.panel_height / 2;",
        "  const ContentLayout snapshot_speaker = calculate_content(frame, snapshot_speaker_request);",
        "  const LayoutSnapshot &snapshot = (rotation == 90 || rotation == 270)",
        "    ? portrait_snapshot : landscape_snapshot;",
        "  check_layout_snapshot(frame, snapshot_tabs, snapshot_content, snapshot_speaker,",
        "                       snapshot_speaker_request.fallback_height, snapshot,",
        "                       rotation_label + \" snapshot\");",
        "  auto check_family = [&](const int *counts, int count_count, const char *family, bool media) {",
        "    for (int i = 0; i < count_count; ++i) {",
        "      const int count = counts[i];",
        "      const bool show = count > 1;",
        "      const int expected_count = media && !show ? 1 : count;",
        "      TabRequest tab_request;",
        "      tab_request.tab_count = media && !show ? 0 : count;",
        "      tab_request.show_tab_bar = show;",
        "      const TabLayout tabs = calculate_tabs(profile, frame, tab_request);",
        "      const std::string scenario = rotation_label + \" \" + family + \" \" + std::to_string(count);",
        "      check_tabs(tabs, frame, expected_count, show, tab_touch_target, scenario + \" tabs\");",
        "      if (!media) continue;",
        "      ContentRequest content_request;",
        "      content_request.show_tab_bar = show;",
        "      content_request.tab_frame_height = tabs.frame_height;",
        "      content_request.tab_content_gap = tabs.content_gap;",
        "      content_request.top_without_tabs = frame.inset * 2;",
        "      content_request.safe_top = show ? 0 : frame.back_inset_y + frame.back_size + scaled_px(12, frame.short_side);",
        "      content_request.minimum_height = 180;",
        "      content_request.fallback_height = frame.panel_height / 2;",
        "      const ContentLayout content = calculate_content(frame, content_request);",
        "      check_content(frame, content, 180, 0, scenario + \" content\");",
        "    }",
        "  };",
        "  check_family(media_counts, media_count, \"media\", true);",
        "  // Climate production lays out its controls directly; only its tab planner is covered here.",
        "  check_family(climate_counts, climate_count, \"climate\", false);",
        "  TabRequest speaker_tab_request;",
        "  speaker_tab_request.tab_count = 4;",
        "  speaker_tab_request.show_tab_bar = true;",
        "  const TabLayout speaker_tabs = calculate_tabs(profile, frame, speaker_tab_request);",
        "  check_tabs(speaker_tabs, frame, 4, true, tab_touch_target, rotation_label + \" media speaker tabs\");",
        "  ContentRequest speaker_content_request;",
        "  speaker_content_request.show_tab_bar = true;",
        "  speaker_content_request.tab_frame_height = speaker_tabs.frame_height;",
        "  speaker_content_request.tab_content_gap = speaker_tabs.content_gap;",
        "  speaker_content_request.minimum_height = 180;",
        "  speaker_content_request.fallback_height = frame.panel_height / 2;",
        "  const ContentLayout speaker_content = calculate_content(frame, speaker_content_request);",
        "  check_content(frame, speaker_content, 180, scrollable_minimum_height,",
        "               rotation_label + \" media speaker content\");",
        "  TabRequest standalone_tab_request;",
        "  standalone_tab_request.tab_count = standalone_tab_count;",
        "  standalone_tab_request.show_tab_bar = false;",
        "  const TabLayout standalone_tabs = calculate_tabs(profile, frame, standalone_tab_request);",
        "  const std::string standalone_label = rotation_label + \" standalone \" + std::to_string(standalone_tab_count);",
        "  check_tabs(standalone_tabs, frame, 1, false, tab_touch_target, standalone_label + \" tabs\");",
        "  ContentRequest standalone_content_request;",
        "  standalone_content_request.show_tab_bar = false;",
        "  standalone_content_request.top_without_tabs = frame.inset * 2;",
        "  standalone_content_request.safe_top = frame.back_inset_y + frame.back_size + scaled_px(12, frame.short_side);",
        "  standalone_content_request.minimum_height = 180;",
        "  standalone_content_request.fallback_height = frame.panel_height / 2;",
        "  const ContentLayout standalone_content = calculate_content(frame, standalone_content_request);",
        "  usability_check(standalone_content.top == standalone_content_request.safe_top,",
        "                  standalone_label + \" safe top\");",
        "  check_content(frame, standalone_content, 180, scrollable_minimum_height, standalone_label + \" content\");",
        "}",
        "int main() {",
    ]
    for index, entry in enumerate(fixtures["layouts"]):
        source.extend(cpp_assertions(entry, index))

    source.extend([
        "  DeviceProfile compact_portrait;",
        "  compact_portrait.layout_family = LayoutFamily::COMPACT_PORTRAIT;",
        "  FrameRequest rotated;",
        "  rotated.screen_width = 800;",
        "  rotated.screen_height = 480;",
        "  const FrameLayout rotated_layout = calculate_frame(compact_portrait, rotated);",
        "  snapshot_check(rotated_layout.short_side == 480, \"compact portrait rotated short side\");",
        "  snapshot_check(rotated_layout.back_inset_x == 30, \"compact portrait rotated back x\");",
        "  snapshot_check(rotated_layout.back_inset_y == 30, \"compact portrait rotated back y\");",
        "  std::cout << \"SNAPSHOT \" << (snapshot_failures ? \"FAIL\" : \"PASS\")",
        "            << \" (\" << snapshot_checks << \" checks, \" << snapshot_failures",
        "            << \" failures)\\n\";",
        "  std::cout << \"USABILITY \" << (usability_failures ? \"FAIL\" : \"PASS\")",
        "            << \" (\" << usability_checks << \" checks, \" << usability_failures",
        "            << \" failures)\\n\";",
        "  return snapshot_failures || usability_failures ? 1 : 0;",
        "}",
    ])

    with tempfile.TemporaryDirectory(prefix="espcontrol-modal-layout-") as tmp:
        tmp_path = Path(tmp)
        source_path = tmp_path / "modal_layout_test.cpp"
        binary_path = tmp_path / "modal_layout_test"
        source_path.write_text("\n".join(source) + "\n", encoding="utf-8")
        subprocess.run(
            [compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", str(source_path), "-o", str(binary_path)],
            check=True,
        )
        result = subprocess.run([str(binary_path)], capture_output=True, text=True)
        print(result.stdout, end="")
        if result.stderr:
            print(result.stderr, end="", file=sys.stderr)
        return result.returncode


def main() -> int:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    assert fixtures.get("version") == 1, "unsupported modal layout fixture version"
    check_fixture_schema(fixtures)
    profiles = load_device_profiles()
    assert_profile_contract(fixtures, profiles)
    return compile_layout_contract(fixtures)


if __name__ == "__main__":
    raise SystemExit(main())
