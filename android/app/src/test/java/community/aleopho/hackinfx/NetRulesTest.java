package community.aleopho.hackinfx;
import org.junit.Test;
import static org.junit.Assert.*;
public class NetRulesTest {
 @Test public void privateAddressesOnly(){for(String h:new String[]{"192.168.1.2","10.0.2.2","172.31.1.1"})assertTrue(NetRules.localHost(h));for(String h:new String[]{"8.8.8.8","127.0.0.1","example.com","192.168.1.999","010.0.0.1","192.168.1.1@evil.com","172.32.0.1"})assertFalse(NetRules.localHost(h));}
 @Test public void strictColorAndCertificatePin(){assertTrue(NetRules.color("9bed4b"));assertFalse(NetRules.color("#9bed4b"));assertTrue(NetRules.pin("a".repeat(64)));assertFalse(NetRules.pin("not-a-certificate"));}
}
