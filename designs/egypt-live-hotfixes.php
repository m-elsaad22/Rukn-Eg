<?php
/**
 * Egypt /eg/ WPCode snippet (type php, location everywhere, auto-insert).
 * Do not wrap in <?php when pasting into WPCode — this file is the repo copy.
 */

$egypt_uri = isset( $_SERVER['REQUEST_URI'] ) ? $_SERVER['REQUEST_URI'] : '';

if ( preg_match( '#/robots\.txt(?:$|\?)#', $egypt_uri ) ) {
	header( 'Content-Type: text/plain; charset=utf-8' );
	echo "User-agent: *\n";
	echo "Allow: /\n";
	echo "Disallow: /wp-admin/\n";
	echo "Allow: /wp-admin/admin-ajax.php\n\n";
	echo "Sitemap: https://www.rukn-eltatawer.com/eg/sitemap_index.xml\n";
	exit;
}

add_filter(
	'wp_robots',
	function ( $robots ) {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? $_SERVER['REQUEST_URI'] : '';
		if ( false !== strpos( $uri, '/en/' ) ) {
			$robots['noindex'] = true;
			$robots['follow']  = true;
		}
		return $robots;
	},
	99
);

add_action(
	'wp_head',
	function () {
		$uri = isset( $_SERVER['REQUEST_URI'] ) ? $_SERVER['REQUEST_URI'] : '';
		if ( false !== strpos( $uri, '/en/' ) ) {
			echo '<meta name="robots" content="noindex,follow">' . "\n";
		}
	},
	1
);
