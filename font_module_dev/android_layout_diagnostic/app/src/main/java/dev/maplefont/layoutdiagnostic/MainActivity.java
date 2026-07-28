package dev.maplefont.layoutdiagnostic;

import android.app.Activity;
import android.graphics.Paint;
import android.graphics.Rect;
import android.graphics.Typeface;
import android.graphics.fonts.Font;
import android.graphics.text.PositionedGlyphs;
import android.graphics.text.TextRunShaper;
import android.os.Bundle;
import android.util.Log;
import android.util.TypedValue;
import android.text.Layout;
import android.view.Gravity;
import android.widget.FrameLayout;
import android.view.View;
import android.view.ViewGroup;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

public final class MainActivity extends Activity {
    private static final String TAG = "MapleLayoutDiagnostic";
    private static final String DEFAULT_CANDIDATE = "/system/fonts/MapleMono-NF-AllCJK-Regular.ttf";
    private static final String SAMPLE_SINGLE = "中文测试 AaÁgjpqy 〱，。！？";
    private static final String SAMPLE_MULTILINE = "中文测试 AaÁgjpqy 〱，。！？\n第二行：固定高度与基线";
    private static final String SAMPLE_FALLBACK = "喵\u1BE0  _ \u032B  _\u0325 \u1BC4 \u0A6D";
    private static final FallbackProbe[] FALLBACK_PROBES = {
            new FallbackProbe(0x1BE0, "isolated", "\u1BE0"),
            new FallbackProbe(0x032B, "with_underscore", "_\u032B"),
            new FallbackProbe(0x0325, "with_underscore", "_\u0325"),
            new FallbackProbe(0x1BC4, "isolated", "\u1BC4"),
            new FallbackProbe(0x0A6D, "isolated", "\u0A6D"),
    };

    private final List<CaseView> cases = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        String requestedCandidatePath = getIntent().getStringExtra("candidate_font");
        final String candidatePath = requestedCandidatePath == null || requestedCandidatePath.isEmpty()
                ? DEFAULT_CANDIDATE
                : requestedCandidatePath;

        Typeface systemTypeface = Typeface.create("sans-serif", Typeface.NORMAL);
        final Typeface candidateTypeface = loadCandidate(candidatePath);

        ScrollView scrollView = new ScrollView(this);
        LinearLayout content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(16), dp(16), dp(16), dp(24));
        scrollView.addView(content);

        addHeading(content, "Maple layout diagnostic");
        addHeading(content, "system sans-serif");
        addCases(content, "system", systemTypeface);
        if (candidateTypeface != null) {
            addHeading(content, "explicit candidate");
            addCases(content, "candidate", candidateTypeface);
        }
        setContentView(scrollView);

        String loaded = candidateTypeface == null ? "failed" : "success";
        Log.i(TAG, "candidate_load=" + loaded + " candidate_path=" + candidatePath);
        content.post(() -> logMeasurements(candidatePath, candidateTypeface != null));
    }

    private Typeface loadCandidate(String candidatePath) {
        try {
            File candidate = new File(candidatePath);
            if (!candidate.isFile() || !candidate.canRead()) {
                Log.w(TAG, "candidate_load_failed path=" + candidatePath + " reason=unreadable");
                return null;
            }
            return Typeface.createFromFile(candidate);
        } catch (RuntimeException exception) {
            Log.w(TAG, "candidate_load_failed path=" + candidatePath, exception);
            return null;
        }
    }

    private void addHeading(LinearLayout parent, String text) {
        TextView heading = new TextView(this);
        heading.setText(text);
        heading.setTextSize(TypedValue.COMPLEX_UNIT_SP, 18);
        heading.setTypeface(Typeface.DEFAULT_BOLD);
        heading.setPadding(0, dp(16), 0, dp(6));
        parent.addView(heading);
    }

    private void addCases(LinearLayout parent, String fontLabel, Typeface typeface) {
        logFallbackProbe(fontLabel, typeface);
        addCase(parent, fontLabel, "fallback_probe", SAMPLE_FALLBACK, typeface, dp(44), true, false, 0);
        addCase(parent, fontLabel, "single_fixed_padding", SAMPLE_SINGLE, typeface, dp(44), true, false, 0);
        addCase(parent, fontLabel, "single_fixed_no_padding", SAMPLE_SINGLE, typeface, dp(44), false, false, 0);
        addCase(parent, fontLabel, "multiline_fixed_padding", SAMPLE_MULTILINE, typeface, dp(72), true, false, 0);
        addCase(parent, fontLabel, "multiline_fixed_no_padding", SAMPLE_MULTILINE, typeface, dp(72), false, false, 0);
        addCase(parent, fontLabel, "title_fixed", "标题 中文 AaÁgjpqy", typeface, dp(48), false, false, 0);
        addCase(parent, fontLabel, "list_row_fixed", "列表项：中文 123 AaÁgjpqy", typeface, dp(52), true, false, 0);
        addCase(parent, fontLabel, "chat_fixed", SAMPLE_MULTILINE, typeface, dp(84), true, false, 0);
        addQqHeaderCase(parent, fontLabel, typeface);
        addQqHeaderOverlapCase(parent, fontLabel, typeface);
        addCase(parent, fontLabel, "button_fixed", "确认 中文 AaÁgjpqy", typeface, dp(44), false, false, 0);
        addCase(parent, fontLabel, "single_auto", SAMPLE_SINGLE, typeface, ViewGroup.LayoutParams.WRAP_CONTENT, false, false, 0);
        addCase(parent, fontLabel, "single_explicit_line_height", SAMPLE_SINGLE, typeface, ViewGroup.LayoutParams.WRAP_CONTENT, false, true, dp(24));
    }

    private void addQqHeaderCase(LinearLayout parent, String fontLabel, Typeface typeface) {
        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.VERTICAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(8), 0, dp(8), 0);
        header.setBackgroundColor(0xFFFFE0F0);

        TextView title = makeTextView("柠檬味的凝萌", typeface, 30, false);
        title.setSingleLine(true);
        TextView online = makeTextView("手机在线", typeface, 14, false);
        online.setSingleLine(true);
        online.setBackgroundColor(0x66FF0000);

        header.addView(title, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(33)
        ));
        header.addView(online, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(20)
        ));

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(55)
        );
        params.bottomMargin = dp(6);
        parent.addView(header, params);
        cases.add(new CaseView(fontLabel, "qq_header_title", title, title.getText().toString(), false, false));
        cases.add(new CaseView(fontLabel, "qq_header_online", online, online.getText().toString(), false, false));
    }

    private void addQqHeaderOverlapCase(LinearLayout parent, String fontLabel, Typeface typeface) {
        FrameLayout header = new FrameLayout(this);
        header.setBackgroundColor(0xFFFFE0F0);
        header.setPadding(dp(8), 0, dp(8), 0);

        TextView online = makeTextView("手机在线", typeface, 14, false);
        online.setSingleLine(true);
        online.setBackgroundColor(0x66FF0000);
        FrameLayout.LayoutParams onlineParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                px(20),
                Gravity.START | Gravity.TOP
        );
        onlineParams.topMargin = px(129);
        header.addView(online, onlineParams);

        TextView title = makeTextView("柠檬味的凝萌", typeface, 30, false);
        title.setSingleLine(true);
        title.setBackgroundColor(0x6633AAFF);
        FrameLayout.LayoutParams titleParams = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                px(107),
                Gravity.START | Gravity.TOP
        );
        titleParams.topMargin = px(22);
        header.addView(title, titleParams);

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                px(149)
        );
        params.bottomMargin = dp(6);
        parent.addView(header, params);
        cases.add(new CaseView(fontLabel, "qq_header_overlap_title", title, title.getText().toString(), false, false));
        cases.add(new CaseView(fontLabel, "qq_header_overlap_online", online, online.getText().toString(), false, false));
    }

    private TextView makeTextView(String text, Typeface typeface, int textSize, boolean includeFontPadding) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTypeface(typeface);
        view.setTextSize(TypedValue.COMPLEX_UNIT_SP, textSize);
        view.setIncludeFontPadding(includeFontPadding);
        view.setGravity(Gravity.CENTER_VERTICAL | Gravity.START);
        view.setTextColor(0xFF202124);
        return view;
    }

    private void addCase(
            LinearLayout parent,
            String fontLabel,
            String caseName,
            String text,
            Typeface typeface,
            int height,
            boolean includeFontPadding,
            boolean explicitLineHeight,
            int lineHeight
    ) {
        TextView view = makeTextView(text, typeface, 20, includeFontPadding);
        view.setBackgroundColor(0xFFE8F5E9);
        view.setPadding(dp(8), 0, dp(8), 0);
        view.setSingleLine(!text.contains("\n"));
        if (explicitLineHeight) {
            view.setLineHeight(lineHeight);
        }

        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                height
        );
        params.bottomMargin = dp(6);
        parent.addView(view, params);
        cases.add(new CaseView(fontLabel, caseName, view, text, includeFontPadding, explicitLineHeight));
    }

    private void logFallbackProbe(String fontLabel, Typeface typeface) {
        Paint paint = new Paint();
        paint.setTypeface(typeface);
        for (FallbackProbe probe : FALLBACK_PROBES) {
            PositionedGlyphs glyphs = TextRunShaper.shapeTextRun(
                    probe.sample,
                    0,
                    probe.sample.length(),
                    0,
                    probe.sample.length(),
                    0.0f,
                    0.0f,
                    false,
                    paint
            );
            Log.i(TAG,
                    "fallback_probe"
                            + " font=" + fontLabel
                            + " codepoint=U+" + String.format("%04X", probe.codePoint)
                            + " context=" + probe.context
                            + " has_glyph=" + paint.hasGlyph(probe.sample)
                            + " glyph_count=" + glyphs.glyphCount()
                            + " glyph_fonts=" + glyphFontPaths(glyphs)
            );
        }
    }

    private String glyphFontPaths(PositionedGlyphs glyphs) {
        StringBuilder paths = new StringBuilder();
        for (int index = 0; index < glyphs.glyphCount(); index++) {
            if (index > 0) {
                paths.append(',');
            }
            Font font = glyphs.getFont(index);
            File file = font.getFile();
            paths.append(file == null ? "<memory>" : file.getName());
        }
        return paths.toString();
    }

    private void logMeasurements(String candidatePath, boolean candidateLoaded) {
        Log.i(TAG, "report_begin candidate_path=" + candidatePath + " candidate_load=" + (candidateLoaded ? "success" : "failed"));
        for (CaseView caseView : cases) {
            TextView view = caseView.view;
            android.graphics.Paint.FontMetricsInt metrics = view.getPaint().getFontMetricsInt();
            Layout layout = view.getLayout();
            Rect layoutBounds = new Rect();
            int lineCount = layout == null ? 0 : layout.getLineCount();
            int firstBaseline = layout == null ? view.getBaseline() : layout.getLineBaseline(0) + view.getTotalPaddingTop();
            int inkTop = Integer.MAX_VALUE;
            int inkBottom = Integer.MIN_VALUE;
            if (layout != null) {
                for (int line = 0; line < lineCount; line++) {
                    layout.getLineBounds(line, layoutBounds);
                    inkTop = Math.min(inkTop, layoutBounds.top + view.getTotalPaddingTop());
                    inkBottom = Math.max(inkBottom, layoutBounds.bottom + view.getTotalPaddingTop());
                }
            }
            if (lineCount == 0) {
                inkTop = 0;
                inkBottom = 0;
            }
            Log.i(TAG,
                    "case=" + caseView.caseName
                            + " font=" + caseView.fontLabel
                            + " padding=" + caseView.includeFontPadding
                            + " explicit_line_height=" + caseView.explicitLineHeight
                            + " view_width=" + view.getWidth()
                            + " view_height=" + view.getHeight()
                            + " line_count=" + lineCount
                            + " baseline=" + firstBaseline
                            + " metrics_top=" + metrics.top
                            + " metrics_ascent=" + metrics.ascent
                            + " metrics_descent=" + metrics.descent
                            + " metrics_bottom=" + metrics.bottom
                            + " metrics_leading=" + metrics.leading
                            + " layout_top=" + inkTop
                            + " layout_bottom=" + inkBottom
                            + " layout_overflow_top=" + Math.max(0, -inkTop)
                            + " layout_overflow_bottom=" + Math.max(0, inkBottom - view.getHeight())
            );
        }
        Log.i(TAG, "report_end");
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int px(int value) {
        return value;
    }

    private static final class CaseView {
        final String fontLabel;
        final String caseName;
        final TextView view;
        final String text;
        final boolean includeFontPadding;
        final boolean explicitLineHeight;

        CaseView(
                String fontLabel,
                String caseName,
                TextView view,
                String text,
                boolean includeFontPadding,
                boolean explicitLineHeight
        ) {
            this.fontLabel = fontLabel;
            this.caseName = caseName;
            this.view = view;
            this.text = text;
            this.includeFontPadding = includeFontPadding;
            this.explicitLineHeight = explicitLineHeight;
        }
    }

    private static final class FallbackProbe {
        final int codePoint;
        final String context;
        final String sample;

        FallbackProbe(int codePoint, String context, String sample) {
            this.codePoint = codePoint;
            this.context = context;
            this.sample = sample;
        }
    }
}
