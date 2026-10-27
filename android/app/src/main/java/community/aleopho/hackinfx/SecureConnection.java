// SPDX-License-Identifier: GPL-3.0-or-later
package community.aleopho.hackinfx;
import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;
import android.util.Base64;
import org.json.JSONObject;
import java.io.*;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.security.*;
import java.security.cert.X509Certificate;
import javax.crypto.*;
import javax.crypto.spec.GCMParameterSpec;
import javax.net.ssl.*;
public final class SecureConnection {
    private static final String ALIAS="HackinFX.Remote.Connection";
    private final Context context;
    public JSONObject profile;
    public SecureConnection(Context context){this.context=context;try{String saved=context.getSharedPreferences("remote",0).getString("connection",null);if(saved!=null){String[] p=saved.split(":");Cipher cipher=Cipher.getInstance("AES/GCM/NoPadding");cipher.init(Cipher.DECRYPT_MODE,key(),new GCMParameterSpec(128,Base64.decode(p[0],Base64.NO_WRAP)));profile=new JSONObject(new String(cipher.doFinal(Base64.decode(p[1],Base64.NO_WRAP)),StandardCharsets.UTF_8));}}catch(Exception ignored){forget();}}
    private javax.crypto.SecretKey key()throws Exception{KeyStore store=KeyStore.getInstance("AndroidKeyStore");store.load(null);if(!store.containsAlias(ALIAS)){KeyGenerator g=KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES,"AndroidKeyStore");g.init(new KeyGenParameterSpec.Builder(ALIAS,KeyProperties.PURPOSE_ENCRYPT|KeyProperties.PURPOSE_DECRYPT).setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build());return g.generateKey();}return ((KeyStore.SecretKeyEntry)store.getEntry(ALIAS,null)).getSecretKey();}
    public void save(JSONObject value)throws Exception{Cipher c=Cipher.getInstance("AES/GCM/NoPadding");c.init(Cipher.ENCRYPT_MODE,key());String data=Base64.encodeToString(c.getIV(),Base64.NO_WRAP)+":"+Base64.encodeToString(c.doFinal(value.toString().getBytes(StandardCharsets.UTF_8)),Base64.NO_WRAP);if(!context.getSharedPreferences("remote",0).edit().putString("connection",data).commit())throw new IOException("Could not store pairing");profile=value;}
    public void forget(){profile=null;context.getSharedPreferences("remote",0).edit().clear().apply();}
    public JSONObject call(JSONObject connection,String path,JSONObject body)throws Exception{
        String host=connection.getString("host"),pin=connection.getString("fingerprint").toLowerCase(java.util.Locale.ROOT);int port=connection.getInt("port");
        if(!NetRules.localHost(host)||!NetRules.pin(pin)||port<1||port>65535)throw new IOException("Use the private IPv4 address and fingerprint displayed by HackinFX");
        TrustManager[] trust={new X509TrustManager(){public X509Certificate[] getAcceptedIssuers(){return new X509Certificate[0];}public void checkClientTrusted(X509Certificate[] c,String a)throws java.security.cert.CertificateException{throw new java.security.cert.CertificateException("Not a client socket");}public void checkServerTrusted(X509Certificate[] chain,String auth)throws java.security.cert.CertificateException{try{if(chain.length==0)throw new GeneralSecurityException();chain[0].checkValidity();byte[] hash=MessageDigest.getInstance("SHA-256").digest(chain[0].getEncoded());StringBuilder actual=new StringBuilder();for(byte b:hash)actual.append(String.format(java.util.Locale.ROOT,"%02x",b&255));if(!MessageDigest.isEqual(actual.toString().getBytes(StandardCharsets.US_ASCII),pin.getBytes(StandardCharsets.US_ASCII)))throw new GeneralSecurityException();}catch(Exception e){throw new java.security.cert.CertificateException("Mac identity does not match. Pair again directly from the Mac.",e);}}}};
        SSLContext tls=SSLContext.getInstance("TLS");tls.init(null,trust,new SecureRandom());HttpsURLConnection request=(HttpsURLConnection)new URL("https://"+host+":"+port+path).openConnection();request.setSSLSocketFactory(tls.getSocketFactory());request.setHostnameVerifier((hostname,session)->hostname.equals(host));request.setConnectTimeout(3500);request.setReadTimeout(5000);request.setInstanceFollowRedirects(false);request.setUseCaches(false);
        String token=connection.optString("token","");if(!token.isEmpty())request.setRequestProperty("Authorization","Bearer "+token);
        try{if(body!=null){request.setRequestMethod("POST");request.setDoOutput(true);request.setRequestProperty("Content-Type","application/json");byte[] bytes=body.toString().getBytes(StandardCharsets.UTF_8);request.setFixedLengthStreamingMode(bytes.length);try(OutputStream out=request.getOutputStream()){out.write(bytes);}}
            int code=request.getResponseCode();InputStream input=code>=400?request.getErrorStream():request.getInputStream();if(input==null)throw new IOException("Mac returned HTTP "+code);ByteArrayOutputStream out=new ByteArrayOutputStream();try(InputStream in=input){byte[] block=new byte[4096];int n;while((n=in.read(block))!=-1){if(out.size()+n>1048576)throw new IOException("Response too large");out.write(block,0,n);}}
            JSONObject value=new JSONObject(out.toString("UTF-8"));if(code!=200)throw new IOException(value.optString("error","Mac returned HTTP "+code));return value;
        }finally{request.disconnect();}
    }
}
