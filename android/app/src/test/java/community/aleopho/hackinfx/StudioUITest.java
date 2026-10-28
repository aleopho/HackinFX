package community.aleopho.hackinfx;
import org.junit.*;
import org.junit.runner.RunWith;
import org.robolectric.*;
import org.robolectric.annotation.*;
import android.graphics.*;
import android.os.Handler;
import android.view.*;
import org.json.*;
import java.lang.reflect.*;
import java.io.*;
import static org.junit.Assert.*;

@RunWith(RobolectricTestRunner.class)
@Config(sdk=35,qualifiers="w411dp-h891dp-xxhdpi")
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@LooperMode(LooperMode.Mode.PAUSED)
public class StudioUITest {
    private void set(Object o,String key,Object value)throws Exception{Field f=o.getClass().getDeclaredField(key);f.setAccessible(true);f.set(o,value);}
    private Object get(Object o,String key)throws Exception{Field f=o.getClass().getDeclaredField(key);f.setAccessible(true);return f.get(o);}
    @Test public void all_workspace_pages_layout_and_render_without_pairing_or_network()throws Exception {
        try(org.robolectric.android.controller.ActivityController<MainActivity> controller=Robolectric.buildActivity(MainActivity.class).create().start()){
            MainActivity a=controller.get();((Handler)get(a,"ui")).removeCallbacksAndMessages(null);
            ((SecureConnection)get(a,"connection")).profile=new JSONObject().put("host","192.168.1.20").put("port",49735);
            ((android.widget.TextView)get(a,"connectionLabel")).setText("CONNECTED");
            JSONObject config=new JSONObject("{\"mode\":\"twinkle\",\"palette\":[\"9bed4b\",\"42d6ce\"],\"brightness\":80,\"speed\":65,\"layers\":[{\"mode\":\"wave\",\"palette\":[\"42d6ce\"],\"blend\":\"screen\",\"opacity\":45}]}");
            JSONArray devices=new JSONArray();for(String[] row:new String[][]{{"keys","Mechanical keyboard","keyboard"},{"gpu","GPU lighting","gpu"},{"ram","Memory lighting","dram"}})devices.put(new JSONObject().put("id",row[0]).put("name",row[1]).put("category",row[2]).put("led_count",48).put("status","ready").put("controllable",true).put("direct",true));
            set(a,"state",new JSONObject().put("scene",config).put("devices",devices).put("active_devices",new JSONArray().put("keys").put("gpu").put("ram")));set(a,"scene",config);
            java.util.Set<String> selected=(java.util.Set<String>)get(a,"selected");selected.add("keys");selected.add("gpu");selected.add("ram");
            Method render=MainActivity.class.getDeclaredMethod("render");render.setAccessible(true);
            for(String tab:new String[]{"Lighting","Devices","Studio","Effects","Settings"}){
                set(a,"tab",tab);render.invoke(a);View page=(View)get(a,"page");page.animate().cancel();page.setAlpha(1);page.setTranslationY(0);
                View view=(View)get(a,"root");view.measure(View.MeasureSpec.makeMeasureSpec(1080,View.MeasureSpec.EXACTLY),View.MeasureSpec.makeMeasureSpec(2340,View.MeasureSpec.EXACTLY));view.layout(0,0,1080,2340);
                android.widget.LinearLayout nav=(android.widget.LinearLayout)get(a,"nav");
                for(int n=0;n<nav.getChildCount();n++){
                    android.widget.LinearLayout item=(android.widget.LinearLayout)nav.getChildAt(n);
                    android.widget.TextView caption=(android.widget.TextView)item.getChildAt(1);
                    assertEquals(android.view.Gravity.CENTER,caption.getGravity());
                    assertFalse(caption.getIncludeFontPadding());
                    assertEquals(item.getWidth(),caption.getWidth());
                    assertTrue(caption.getHeight()>0);
                    assertTrue(caption.getBottom()<=item.getHeight());
                    assertTrue(caption.getPaint().measureText(caption.getText().toString())<=caption.getWidth());
                    System.out.println("NAV "+caption.getText()+" "+caption.getTop()+".."+caption.getBottom()+" parent="+item.getHeight()+" text="+caption.getTextSize()+" baseline="+caption.getBaseline());
                }
                assertTrue(view.getMeasuredWidth()>0);Bitmap image=Bitmap.createBitmap(1080,2340,Bitmap.Config.ARGB_8888);view.draw(new Canvas(image));
                File dir=new File("build/outputs/design");assertTrue(dir.exists()||dir.mkdirs());try(OutputStream out=new FileOutputStream(new File(dir,"remote-"+tab.toLowerCase()+"-sample.png"))){assertTrue(image.compress(Bitmap.CompressFormat.PNG,100,out));}image.recycle();
            }
            ((Handler)get(a,"ui")).removeCallbacksAndMessages(null);
        }
    }
}
