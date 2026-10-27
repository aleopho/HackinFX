// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
import android.content.Context;
import android.graphics.*;
import android.os.SystemClock;
import android.view.View;
/** Animated gallery illustration; physical rendering remains on the Mac. */
public final class EffectPreview extends View {
    private final Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);private final Rect visible=new Rect();
    private final String mode;private final int[] palette;
    public EffectPreview(Context c,String mode,int[] palette){super(c);this.mode=mode;this.palette=palette.length==0?new int[]{0xff9bed4b,0xff42d6ce,0xff9f8bff}:palette;setLayerType(LAYER_TYPE_SOFTWARE,null);setContentDescription(mode+" effect illustration");}
    @Override protected void onDraw(Canvas c){super.onDraw(c);boolean animate=hasWindowFocus()&&android.animation.ValueAnimator.areAnimatorsEnabled();double t=animate?SystemClock.uptimeMillis()/1000.0:0;float w=getWidth(),h=getHeight();
        paint.setShader(new LinearGradient(0,0,w,h,new int[]{0xff142b2b,0xff090e13},null,Shader.TileMode.CLAMP));c.drawRoundRect(0,0,w,h,18,18,paint);paint.setShader(null);
        paint.setColor(0x183e7270);paint.setStrokeWidth(1);for(int x=0;x<w;x+=24)c.drawLine(x,0,x,h,paint);for(int y=0;y<h;y+=24)c.drawLine(0,y,w,y,paint);
        boolean rainbow=mode.contains("spectrum")||mode.contains("rainbow")||mode.contains("rain");boolean spark=mode.contains("twinkle")||mode.contains("spark")||mode.contains("star")||mode.contains("firefly");boolean steady=mode.equals("static")||mode.equals("gradient");
        for(int i=0;i<60;i++){float x=(i%15+.5f)*w/15,y=(i/15+.5f)*h/4;double phase=i*.91+t*1.7;double b=steady?1:spark?Math.pow(Math.max(0,Math.sin(i*2.913+t*(.5+(i%7)*.13))),7):.22+.78*(.5+.5*Math.sin(phase));int col=rainbow?Color.HSVToColor(new float[]{(float)((i*6+t*35)%360),.75f,1}):palette[Math.floorMod((int)(i/15+t*.4),palette.length)];paint.setColor(col);paint.setAlpha((int)(30+225*b));paint.setShadowLayer(7,0,0,col);float radius=(float)(2+3*b);if(mode.contains("wave")||mode.contains("aurora"))y+=(float)Math.sin(i*.35+t)*h*.12;c.drawCircle(x,y,radius,paint);}paint.clearShadowLayer();
        if(animate&&isShown()&&getGlobalVisibleRect(visible))postInvalidateDelayed(50);
    }
    @Override protected void onWindowVisibilityChanged(int visibility){super.onWindowVisibilityChanged(visibility);if(visibility==VISIBLE)invalidate();}
    @Override public void onWindowFocusChanged(boolean focus){super.onWindowFocusChanged(focus);if(focus)invalidate();}
}
