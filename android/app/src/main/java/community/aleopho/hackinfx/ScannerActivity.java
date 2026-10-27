// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.*;
import com.google.zxing.BarcodeFormat;
import com.google.zxing.ResultPoint;
import com.journeyapps.barcodescanner.*;
import java.util.*;

/** Dedicated camera lifecycle; no legacy capture intent or orientation locking. */
public final class ScannerActivity extends Activity {
    public static final int REQUEST=7415;
    private DecoratedBarcodeView scanner;
    private TextView status;
    private boolean active=false,completed=false;
    @Override public void onCreate(Bundle state){
        super.onCreate(state);
        LinearLayout root=new LinearLayout(this);root.setOrientation(LinearLayout.VERTICAL);root.setPadding(24,40,24,28);root.setBackgroundColor(Color.rgb(9,14,16));
        TextView title=new TextView(this);title.setText("Pair HackinFX");title.setTextSize(24);title.setTextColor(0xffc4f37a);root.addView(title);
        status=new TextView(this);status.setText("Scan the QR code displayed in Mac Settings → Android Remote.");status.setTextColor(0xffe7efeb);status.setPadding(0,20,0,20);root.addView(status);
        scanner=new DecoratedBarcodeView(this);scanner.setStatusText("");scanner.getBarcodeView().setDecoderFactory(new DefaultDecoderFactory(Collections.singletonList(BarcodeFormat.QR_CODE)));root.addView(scanner,new LinearLayout.LayoutParams(-1,0,1));
        scanner.getBarcodeView().addStateListener(new CameraPreview.StateListener(){public void previewSized(){}public void previewStarted(){}public void previewStopped(){}public void cameraClosed(){}public void cameraError(Exception e){status.setText("Camera could not open. Close other camera apps or use Paste pairing details.");}});
        Button back=new Button(this);back.setText("Back to pairing");back.setOnClickListener(v->finish());root.addView(back);setContentView(root);
        scanner.decodeContinuous(new BarcodeCallback(){public void barcodeResult(BarcodeResult result){if(completed||result.getText()==null)return;completed=true;scanner.pause();setResult(RESULT_OK,new Intent().putExtra("pairing",result.getText()));finish();}public void possibleResultPoints(List<ResultPoint> points){}});
    }
    @Override protected void onResume(){super.onResume();active=true;if(checkSelfPermission(Manifest.permission.CAMERA)==PackageManager.PERMISSION_GRANTED)startCamera();else requestPermissions(new String[]{Manifest.permission.CAMERA},31);}
    private void startCamera(){if(active&&!completed)try{scanner.resume();}catch(RuntimeException e){status.setText("Camera unavailable. Use Paste pairing details or manual pairing.");}}
    @Override public void onRequestPermissionsResult(int request,String[] permissions,int[] grants){super.onRequestPermissionsResult(request,permissions,grants);if(request==31){if(grants.length>0&&grants[0]==PackageManager.PERMISSION_GRANTED)startCamera();else status.setText("Camera permission denied. Enable it in Android Settings or use Paste pairing details.");}}
    @Override protected void onPause(){active=false;scanner.pause();super.onPause();}
}
