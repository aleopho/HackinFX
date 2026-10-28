// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
import android.content.Context;
import android.graphics.*;
import android.graphics.drawable.Drawable;
import android.view.*;
import java.util.function.IntConsumer;

/** Code-owned orbital identity and lightweight native drawing primitives. */
final class StudioGraphics {
    static final int MINT=0xffc4f37a,INK=0xffedf4ef;
    static final class Background extends Drawable {
        final Paint p=new Paint(3);
        public void draw(Canvas c){Rect b=getBounds();c.drawColor(0xff080c10);p.setShader(new RadialGradient(b.width(),0,Math.max(1,b.width()),new int[]{0xff15302b,0x00080c10},null,Shader.TileMode.CLAMP));c.drawRect(b,p);p.setShader(null);}
        public void setAlpha(int a){}public void setColorFilter(ColorFilter f){}public int getOpacity(){return PixelFormat.OPAQUE;}
    }
    static final class Glyph extends View {
        final Paint p=new Paint(3);final String kind;int tint=MINT;
        Glyph(Context c,String kind){super(c);this.kind=kind;setImportantForAccessibility(IMPORTANT_FOR_ACCESSIBILITY_NO);}
        void tint(int color){tint=color;invalidate();}
        protected void onDraw(Canvas c){super.onDraw(c);c.save();c.translate(getWidth()/2f,getHeight()/2f);float unit=Math.min(getWidth(),getHeight())/28f;c.scale(unit,unit);p.setColor(tint);p.setStrokeWidth(1.6f);p.setStyle(Paint.Style.STROKE);p.setStrokeCap(Paint.Cap.ROUND);p.setStrokeJoin(Paint.Join.ROUND);
            if(kind.equals("Lighting")){c.drawCircle(0,0,4,p);for(int i=0;i<8;i++){c.save();c.rotate(i*45);c.drawLine(0,-8,0,-11,p);c.restore();}}
            else if(kind.equals("Devices")){c.drawRoundRect(-9,-8,9,4,2,2,p);c.drawLine(-6,8,6,8,p);c.drawLine(0,4,0,8,p);}
            else if(kind.equals("Studio")){for(int i=0;i<3;i++){Path a=new Path();a.moveTo(-10,-5+i*5);a.lineTo(0,-10+i*5);a.lineTo(10,-5+i*5);a.lineTo(0,i*5);a.close();c.drawPath(a,p);}}
            else if(kind.equals("Settings")){c.drawCircle(0,0,6,p);c.drawCircle(0,0,2,p);for(int i=0;i<8;i++){c.save();c.rotate(i*45);c.drawLine(0,-8,0,-10,p);c.restore();}}
            else {Path a=new Path();a.moveTo(0,-11);a.cubicTo(1,-2,2,-1,10,0);a.cubicTo(2,1,1,2,0,11);a.cubicTo(-1,2,-2,1,-10,0);a.cubicTo(-2,-1,-1,-2,0,-11);c.drawPath(a,p);c.drawLine(8,-11,8,-5,p);c.drawLine(5,-8,11,-8,p);}
            c.restore();}
    }
    static final class ColorWheel extends View {
        final Paint p=new Paint(3);final float[] hsv={90,0.7f,1};final IntConsumer change;
        ColorWheel(Context c,int color,IntConsumer change){super(c);Color.colorToHSV(color,hsv);this.change=change;setContentDescription("Color wheel. Hex field below provides accessible precise color entry.");}
        protected void onDraw(Canvas c){float x=getWidth()/2f,y=getHeight()/2f,r=Math.min(x,y)-12;c.save();c.translate(x,y);p.setShader(new SweepGradient(0,0,new int[]{Color.RED,Color.MAGENTA,Color.BLUE,Color.CYAN,Color.GREEN,Color.YELLOW,Color.RED},null));c.drawCircle(0,0,r,p);p.setShader(new RadialGradient(0,0,Math.max(1,r),Color.WHITE,Color.TRANSPARENT,Shader.TileMode.CLAMP));c.drawCircle(0,0,r,p);p.setShader(null);double a=-hsv[0]*Math.PI/180;p.setColor(Color.BLACK);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(6);float px=(float)Math.cos(a)*hsv[1]*r,py=(float)Math.sin(a)*hsv[1]*r;c.drawCircle(px,py,9,p);p.setColor(Color.WHITE);p.setStrokeWidth(3);c.drawCircle(px,py,9,p);p.setStyle(Paint.Style.FILL);c.restore();}
        public boolean onTouchEvent(android.view.MotionEvent e){if(e.getAction()!=MotionEvent.ACTION_DOWN&&e.getAction()!=MotionEvent.ACTION_MOVE&&e.getAction()!=MotionEvent.ACTION_UP)return true;float dx=e.getX()-getWidth()/2f,dy=e.getY()-getHeight()/2f,r=Math.min(getWidth(),getHeight())/2f-12;hsv[0]=(float)((-Math.atan2(dy,dx)*180/Math.PI+360)%360);hsv[1]=Math.min(1,(float)Math.hypot(dx,dy)/Math.max(1,r));hsv[2]=1;change.accept(Color.HSVToColor(hsv));invalidate();if(e.getAction()==MotionEvent.ACTION_UP)performClick();return true;}
        public boolean performClick(){super.performClick();return true;}
    }
}
